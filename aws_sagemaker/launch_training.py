"""Upload prepared CSV channels and start a capped, billable SageMaker job."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = ROOT / "output/sagemaker/estateiq_anomaly_v1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--bucket", required=True, help="S3 bucket in the same AWS Region as the training job")
    parser.add_argument("--role-arn", required=True, help="SageMaker execution role ARN; do not pass access keys")
    parser.add_argument("--region", required=True)
    parser.add_argument("--instance-type", default="ml.m5.large", help="CPU training instance; no GPU needed for this dataset")
    parser.add_argument("--max-run-seconds", type=int, default=3600)
    parser.add_argument("--false-alert-budget", type=float, default=1.0)
    parser.add_argument("--confirm-billable-job", action="store_true", help="Required before a cloud training job is created")
    args = parser.parse_args()
    if not args.confirm_billable_job:
        parser.error("This starts billable AWS compute. Review the AWS cost/region first, then pass --confirm-billable-job.")
    manifest = args.data_dir / "manifest.json"
    if not manifest.is_file():
        parser.error(f"Prepared manifest not found: {manifest}. Run prepare_data.py first.")
    channels = ("train", "validation", "test", "building_holdout")
    for channel in channels:
        if not any((args.data_dir / channel).glob("*.csv")):
            parser.error(f"Prepared CSV channel missing: {args.data_dir / channel}")

    # Imports after explicit billable-job confirmation avoid accidental AWS calls.
    import boto3
    import sagemaker
    from sagemaker.sklearn.estimator import SKLearn

    boto_session = boto3.Session(region_name=args.region)
    session = sagemaker.Session(boto_session=boto_session)
    prefix = f"estateiq/anomaly-v1/{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    inputs = {
        channel: session.upload_data(
            path=str(args.data_dir / channel), bucket=args.bucket,
            key_prefix=f"{prefix}/input/{channel}",
        )
        for channel in channels
    }
    estimator = SKLearn(
        entry_point="train.py", source_dir=str(SCRIPT_DIR), role=args.role_arn,
        instance_count=1, instance_type=args.instance_type,
        framework_version="1.4-2", py_version="py3",
        output_path=f"s3://{args.bucket}/{prefix}/model-artifacts",
        sagemaker_session=session, max_run=args.max_run_seconds,
        hyperparameters={"false-alert-budget": args.false_alert_budget},
        tags=[{"Key": "Project", "Value": "EstateIQ"}, {"Key": "Purpose", "Value": "SyntheticAnomalyModelTraining"}],
    )
    print(f"Starting SageMaker training job in {args.region}; input prefix: s3://{args.bucket}/{prefix}/input")
    estimator.fit(inputs=inputs, job_name=f"estateiq-anomaly-v1-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}", wait=True, logs="All")
    print("Training completed. Model artifact:", estimator.model_data)


if __name__ == "__main__":
    main()
