from enum import Enum


class InverterMode(Enum):
    FCRDD = "Fcr-d down"
    FCRDU = "Fcr-d up"
    FULLYCHARGED = "Standby fully charged"
    STANDBY = "Standby"
    BACKUPSOC = "Standby backup soc"
    CHARGING = "Charging"
    DISCHARGING = "Discharging"
    CHARGESOC = "Charging to keep backup soc"
    FAULT = "Fault"
    SELFUSE = "Selfuse"
