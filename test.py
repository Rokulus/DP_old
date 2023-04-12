from fmpy import *
from fmpy.util import fmu_info

import shutil

import platform
#print(platform.architecture())

import matlab.engine
import numpy as np

# path to the FMU
#filename = 'myPIDredukLietadlo.fmu'
#filename = 'symetry1.fmu'


# get information about the     model
#dump(filename)
#model_description = read_model_description(filename)
#print(model_description)
#result = simulate_fmu(filename)
#print(result)
#print(result.dtype)
# print(result[0])
# print(result[1])
# print("---------------------------------------------")
# print(result['time'])
# print("---------------------------------------------")
# print(result['h'])
# print("---------------------------------------------")
# print(str(result['g']))


#graph
#result = simulate_fmu(filename)
#plot_result(result)


#print(fmu_info(filename))

# md = read_model_description(filename, validate=False)
# platforms = supported_platforms(filename)
# #print(md.modelVariables)
# for v in md.modelVariables:
#     print(v.description)

#shutil.make_archive('templates/BouncingBall', 'zip', 'assets/models/BouncingBall')

engs = matlab.engine.find_matlab()
if not engs:
    eng = matlab.engine.start_matlab()
else:
    eng = matlab.engine.connect_matlab(engs[0])

#eng.eval("open_system('D:\DP\minimal_fastapi\minimal_fastapi\uploaded_matlab_files\model');", nargout=0)
# file = "model"
# eng.open_system(f'D:\\DP\\minimal_fastapi\\minimal_fastapi\\uploaded_matlab_files\\{file}', nargout=0)
# eng.quit()

eng.set_param('model/Gain','Gain', str(2), nargout=0)
eng.sim('model')
eng.eval('x = out.data;',nargout=0)
eng.eval('t = out.tout;',nargout=0)
x = eng.workspace['x']
t = eng.workspace['t']
eng.quit()
#tu menim matlab double na array ktory sa mi vrati v response
# TODO treba najst ine riesenie lebo toto bude pomale pri vacsich datach
c = [[] for _ in range(len(x[0]))]
for i in range(len(x[0])):
    for j in range(len(x)):
        c[i].append(x[j][i])
#print(type(p))
#print(p[:][0])
#print(c)

data = np.array(x)
data_time = np.array(t)
key = "data"
final_result = []
for value in data:
    temp_dict = {}
    temp_dict.update({key: value[0]})
    final_result.append(temp_dict)

key = "time"
for i, value in enumerate(data_time):
    final_result[i].update({key: value[0]})


print(final_result)
