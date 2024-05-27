import time
from decimal import Decimal


TIME_UTS_DURATION_UNITS = (
    ('d', 60*60*24),
    ('h', 60*60),
    ('min', 60),
    ('s', 1),
)


TIME_LTS_DURATION_UNITS = (
    ('s ', 1),
    ('ms', 1e-3),
    ('µs', 1e-6),
    ('ns', 1e-9),
)


def human_time_duration(seconds):
    assert type(seconds) in [float, int], f'seconds ({type(seconds)}) must be a float or int'
    if seconds == 0:
        return 0
    if seconds <= 60 :
        for unit, div in TIME_LTS_DURATION_UNITS:
            if seconds >= div :
                return f"{seconds/div:11.2f}{unit}"
        return f"{Decimal(seconds):11.2E}s "
    else :
        if seconds < 3600 :
            return f"{seconds//60:6.0f}min{seconds%60:2.0f}s"
        else :
            h = seconds // 3600
            m = (seconds - h * 3600) // 60
            s = seconds - (h * 3600) - (m * 60)
            return f"{h:3}h{m:2}min{s:2}s"

if __name__ == "__main__":
    
    for i in range(0, 11):
        print(f"{10**-i:8}", human_time_duration(10**-i) \
            , human_time_duration(2*10**-i)
            , human_time_duration(10**-i - 10**(-i-3))
            , human_time_duration(1/3*10**-i))

    for i in [1, 2, 59, 60, 61, 144, 3599, 3600, 3601, 3660, 3661, 3600*120]:
        print(f"{i:8}",human_time_duration(i))
    