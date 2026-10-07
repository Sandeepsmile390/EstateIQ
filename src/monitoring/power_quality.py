"""
Power Quality & Grid Reliability Module (src/monitoring/power_quality.py).
Monitors electrical parameters: voltage deviation, frequency deviation, power factor, Total Harmonic Distortion (THD),
and phase voltage imbalance.
"""

from typing import Dict, Any

class PowerQualityMonitor:
    def __init__(self, nominal_voltage_v: float = 415.0, nominal_frequency_hz: float = 50.0):
        self.nominal_v = nominal_voltage_v
        self.nominal_freq = nominal_frequency_hz

    def evaluate_power_quality(
        self,
        voltage_v: float = 412.0,
        frequency_hz: float = 49.95,
        power_factor: float = 0.92,
        thd_percent: float = 3.2,
        phase_imbalance_pct: float = 1.2
    ) -> Dict[str, Any]:
        """Evaluates grid power quality and flags operational warnings."""
        v_dev_pct = abs((voltage_v - self.nominal_v) / self.nominal_v) * 100.0
        freq_dev = abs(frequency_hz - self.nominal_freq)

        warnings = []
        if power_factor < 0.85:
            warnings.append("POOR_POWER_FACTOR (Low power factor penalty risk)")
        if thd_percent > 5.0:
            warnings.append("HIGH_HARMONIC_DISTORTION (THD > 5.0%)")
        if v_dev_pct > 6.0:
            warnings.append("VOLTAGE_DEVIATION_WARNING (Voltage fluctuation > 6%)")
        if phase_imbalance_pct > 2.5:
            warnings.append("PHASE_IMBALANCE_WARNING (Phase unbalance > 2.5%)")

        status = "POWER_QUALITY_WARNING" if warnings else "POWER_QUALITY_OPTIMAL"
        quality_score = max(0.0, 100.0 - (v_dev_pct * 3.0 + thd_percent * 2.0 + (1.0 - power_factor) * 50.0))

        return {
            "status": status,
            "quality_score": round(quality_score, 1),
            "voltage_v": voltage_v,
            "voltage_deviation_pct": round(v_dev_pct, 2),
            "frequency_hz": frequency_hz,
            "frequency_deviation_hz": round(freq_dev, 3),
            "power_factor": power_factor,
            "thd_percent": thd_percent,
            "phase_imbalance_percent": phase_imbalance_pct,
            "warnings_flagged": warnings,
            "provenance": "DERIVED"
        }
