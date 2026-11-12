# EstateIQ model training on SageMaker AI

This folder trains a **learned anomaly-evidence component** on SageMaker AI. It does not claim that the whole EstateIQ-DIF decision pipeline is a trained model. The current DIF path remains the contextual baseline, quality gate, rule evidence, persistence gate, business-impact calculation, and decision logic. The resulting Random Forest artifact must pass the evaluation below before anyone wires it into live DIF decisions.

## What it trains

- Candidate: EstateIQ-Learned-Anomaly-Evidence-v1, using the same 16 telemetry/time-derived input features as the local benchmark's Random Forest.
- Label: `building_fault` versus `nominal`. `sensor_quality_fault` rows are excluded because the live application has a separate sensor-health engine.
- Features never include `anomaly_flag`, `anomaly_type`, `fault_category`, or `event_id`.
- Validation selects a threshold that maximizes F1 while meeting the configured false-alert budget, default 1 false alert per building-day. If validation cannot satisfy the budget, the model fails closed at a threshold that emits no alerts and records that the budget was not met.
- Test channels are used only for reporting. `building_holdout` is an entirely unseen building and is not used for training or threshold calibration.
- CPU only. This dataset is small; GPU training is unnecessary.

The source dataset currently has 86,880 synthetic rows across five buildings, including 762 building-fault rows, 92 sensor-quality-fault rows, and 15 injected events. These counts are synthetic-data evidence and do not establish real-world accuracy.

## Prepare channels locally

From the repository root:

```powershell
python aws_sagemaker/prepare_data.py
```

The default chronological cutoffs match the project benchmark: training through 15 March 2026, validation through 31 March 2026, and future testing from April onward. `BLD004` is excluded from all three and exported as the separate unseen-building holdout. The resulting CSV channels and source SHA-256 manifest are written under `output/sagemaker/estateiq_anomaly_v1/`.

## Requirements before launching a cloud job

1. An AWS account, selected Region, S3 bucket in that Region, and a SageMaker execution IAM role with S3 input/output permissions.
2. Local AWS CLI/SDK credentials using an AWS profile or another supported credential provider. Never place AWS access keys in this repository or send them in chat.
3. Install the launcher dependencies: `python -m pip install boto3 sagemaker`.
4. Review SageMaker and S3 pricing for your chosen Region and instance before launching.

The launcher requires `--confirm-billable-job` to start compute. It sets a one-hour maximum runtime by default and creates **a training job only**—it does not deploy or leave a hosted endpoint running. SageMaker reads input from S3 channels and writes a compressed model artifact to the specified S3 output path. See [SageMaker training input/output paths](https://docs.aws.amazon.com/sagemaker/latest/dg/model-train-storage-env-var-summary.html) and [custom Scikit-learn training](https://docs.aws.amazon.com/sagemaker/latest/dg/sklearn.html).

Example, after preparing data and reviewing AWS charges:

```powershell
python aws_sagemaker/launch_training.py `
  --bucket YOUR_S3_BUCKET `
  --role-arn arn:aws:iam::YOUR_ACCOUNT_ID:role/YOUR_SAGEMAKER_EXECUTION_ROLE `
  --region YOUR_AWS_REGION `
  --confirm-billable-job
```

The job logs validation, future-test, and held-out-building metrics; SageMaker stores `metrics.json` in its training-output archive separately from `model.tar.gz`. Review event capture, precision/recall, PR-AUC, and false alerts per building-day. Do not claim “accuracy” alone: the nominal class dominates the dataset. Do not promote the candidate if it fails the false-alert budget or performs poorly on the unseen-building holdout.

## After training

Download and inspect the artifact and metrics, reproduce the benchmark locally, and compare against EstateIQ-DIF using the same split and alert budget. Only after that comparison should the artifact be integrated into `EstateIQAdaptiveEnsemble` as one additional evidence source. Keep the current DIF decision gates and the sensor-health engine active. The SageMaker artifact is not yet wired into live inference, and training does not deploy an endpoint.

## Important limitations

- The source data is synthetic and has only 15 injected events; event diversity is still limited. Add independent random seeds and new fault scenarios before treating the scores as robust.
- The threshold is calibrated only on validation. Never change it based on final test/holdout results and then report those same results as unbiased.
- The model is trained on electricity features. Water, air, and waste require separate, correctly labeled domain datasets and models; this package does not claim to train those sensors.
- SageMaker training and S3 storage incur charges. The scripts do not automatically upload data, start a job, or deploy an endpoint unless the launcher is explicitly run with `--confirm-billable-job`.
