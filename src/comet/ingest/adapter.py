import pandas as pd

from comet.core.types import Channel, Run


def split_unit(column: str) -> tuple[str, str]:
    """'PTRun_psi' -> ('PTRun', 'psi').

    The unit is everything after the last underscore.
    """
    name, _, unit = column.rpartition("_")
    if not name or not unit:
        raise ValueError(f"column {column!r} has no unit suffix")
    return name, unit


class QRETCsvAdapter:
    def ingest(self, file: str, tags: dict[str, list[str]]) -> Run:
        channels: dict[str, Channel] = {}

        df = pd.read_csv(file)

        timestamp_col = "device_timestamp_s"
        sensor_cols = [col for col in df.columns if col != timestamp_col]

        for sensor in sensor_cols:
            # Select the timestamp and the specific sensor
            # then drop rows where the sensor is NaN
            sensor_df = df[[timestamp_col, sensor]].dropna(subset=[sensor])

            times = sensor_df[timestamp_col].to_numpy()
            values = sensor_df[sensor].to_numpy()

            name, unit = split_unit(sensor)

            channels[name] = Channel(
                name=name,
                times=times,
                values=values,
                unit=unit,
                tags=frozenset(tags.get(name, [])),
            )

        return Run(channels=channels)
