import time
from custom_profiler import profiler, profiler_lbl, magic_profiler, profiler_collecteur, Interactivity

@profiler
def my_func():
    a = [1] * (10 ** 6)
    b = [2] * (2 * 10 ** 7)  
    time.sleep(2)
    del b
    time.sleep(2)
    return a

a = my_func()

@profiler
def f_f():
    b = [2] * (2 * 10 ** 7)  
    time.sleep(3)
    a = my_func()
    time.sleep(3)

f_f()


with magic_profiler("my_code_to_prof") :
    d = [1] * (10 ** 6)
    e = [2] * (2 * 10 ** 7)  
    time.sleep(3)
    del e

@profiler_lbl
def my_func_lbl():
    a = [1] * (10 ** 6)
    b = [2] * (2 * 10 ** 7)  
    time.sleep(2)
    del b
    time.sleep(2)
    return a

a = my_func_lbl()

"""
import logging

logging.basicConfig(filename='custom_profiler.log', filemode='w')

loggername = " ⚡" # logger name
addCustumLvl = False # add "PROFILER" level in logger

pc = profiler_collecteur()
pc.options(interactivity = Interactivity.ENABLE # ENABLE / MF_NO_INTERAC / DISABLE / AUTO / OFF
          , use_logger = True
          , logger_name = loggername
          , add_custom_level = addCustumLvl
          , profiler_level = 25)

#Log in consol
#ch = logging.StreamHandler()
#logger = logging.getLogger("⚡")
#logger.addHandler(ch)

#log in file
#logger.info('Finished')
#self.logger("strlog")

logger = logging.getLogger(loggername)
if addCustumLvl :
    logger.profiler(pc.__str__())
else :
    logger.info(pc.__str__())
"""