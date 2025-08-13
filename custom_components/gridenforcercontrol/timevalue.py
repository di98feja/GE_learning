from datetime import datetime


class TimeValue:
    def __init__(self, start: datetime, end: datetime, value: float, sell_value: float):
        """Initializes a TimeValue object with start time, end time, and a value.
        
        :param start: The start datetime.
        :param end: The end datetime.
        :param value: A numerical value associated with the time range.
        """
        self._start = start
        self._end = end
        self._value = value
        self._sell_value = sell_value
        self._mode = None

    @property
    def start(self) -> datetime:
        """Getter for the start datetime."""
        return self._start

    @start.setter
    def start(self, start: datetime):
        """Setter for the start datetime."""
        if start >= self._end:
            raise ValueError("Start time must be before the end time.")
        self._start = start

    @property
    def end(self) -> datetime:
        """Getter for the end datetime."""
        return self._end

    @end.setter
    def end(self, end: datetime):
        """Setter for the end datetime."""
        if end <= self._start:
            raise ValueError("End time must be after the start time.")
        self._end = end

    @property
    def value(self) -> float:
        """Getter for the value."""
        return self._value

    @value.setter
    def value(self, value: float):
        """Setter for the value."""
        if value < 0:
            raise ValueError("Value must be non-negative.")
        self._value = value

    @property
    def sell_value(self) -> float:
        """Getter for the value."""
        return self._sell_value

    @sell_value.setter
    def sell_value(self, sell_value: float):
        """Setter for the value."""
        if sell_value < 0:
            raise ValueError("Value must be non-negative.")
        self._sell_value = sell_value

    @property
    def mode(self) -> str:
        """Getter for the mode."""
        return self._mode

    @mode.setter
    def mode(self, value: str):
        """Setter for the mode."""
        self._mode = value

    def __repr__(self):
        return f"TimeValue(start={self.start}, end={self.end}, value={self.value}, sell_value={self.sell_value}, mode={self.mode})\n"

    def to_dict(self):
        return {
            "start": self.start,
            "end": self.end,
            "value": self.value,
            "sell_value": self.sell_value,
            "mode": self.mode,
        }
