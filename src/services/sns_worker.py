"""Run the durable SNS Telegram outbox worker: python -m src.services.sns_worker."""
import logging
import os
import time

from src.services.sns import deliver_telegram_outbox


def main() -> None:
    interval = max(2, int(os.getenv("SNS_WORKER_INTERVAL_SECONDS", "5")))
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    log = logging.getLogger("estateiq.sns.worker")
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        log.error("TELEGRAM_BOT_TOKEN is not configured; worker will exit.")
        return
    log.info("EstateIQ SNS Telegram outbox worker started")
    try:
        while True:
            try:
                result = deliver_telegram_outbox()
                if result["sent"] or result["failed"]:
                    log.info("SNS delivery batch: %s", result)
            except Exception:
                log.exception("SNS worker batch failed")
            time.sleep(interval)
    except KeyboardInterrupt:
        log.info("SNS worker stopped")


if __name__ == "__main__":
    main()
