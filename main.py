import json
import os
import time
import matlab.engine
import asyncio
import threading

from typing import Union, List, Annotated, Optional
from fastapi import FastAPI, Request, Query, File, UploadFile, Depends, Body, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from fmpy import *
from fmpy.util import *
from dataclasses import dataclass

tags_metadata = [
    {
        "name": "FMU",
        "description": "Operation only with fmu files",
    },
    {
        "name": "MATLAB",
        "description": "matlab",
        "externalDocs": {
            "description": "tags info",
            "url": "https://fastapi.tiangolo.com/tutorial/metadata/",
        },
    },
]

app = FastAPI(openapi_tags=tags_metadata)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/js", StaticFiles(directory="js"), name="js")

templates = Jinja2Templates(directory="templates")

@dataclass
class Model:
    startTime: float = Query(None, description="describes A")
    stopTime: float = Query(None, description="describes A")
    stepSize: float = None
    solver: str = Query("CVode", description="describes solver")
    relative_tolerance: float = Query(None, description="describes A")
    startValues: str = None
    outputInterval: int = None
    outputValues: str = Query(None, description="Must be in format: variable1,variable2")

@app.get("/")
async def read_root(request: Request):
    f = open('assets/models/BouncingBall/BouncingBall.js', 'r')
    content = f.read()
    f.close()

    return templates.TemplateResponse("home.html", {
        "request": request,
        "somevar": 2,
        "contentOfJS": content,
        "dataSets": json.dumps(["h","e"])
    })

#TODO: validacie pridat
@app.get("/model/{modelName}")
def show_model(request: Request, modelName: str, modelMode: Union[str, None] = "continuous", stopTime: float = 10, dataSets: List[str] = Query([]), stepSize: float = 0.1, interval: float = 30):
    # if(os.path.isdir(f"/var/www/fastapi/assets/models/{modelName}") == False):
    #     return {"Model does not exist"}
    f = open(f'assets/models/{modelName}/{modelName}.js', 'r')
    content = f.read()
    f.close()
    return templates.TemplateResponse("model.html", {
        "request": request,
        "modelName": modelName,
        "modelMode": modelMode,
        "stopTime": stopTime,
        "dataSets": json.dumps(dataSets),
        "stepSize": stepSize,
        "interval": interval,
        "contentOfJS": content
    })

#include_in_schema=False skryje API z docs
@app.get("/modelInfo", include_in_schema=False)
def show_model_info(request: Request):
    path = "assets/models_xml"
    files = os.listdir(path)
    return templates.TemplateResponse("info.html", {
        "request": request,
        "files": json.dumps(files)
    })

@app.get("/model2/{modelName}")
def show_model(request: Request, modelName: str, model: Model):
    f = open(f'assets/models/{modelName}/{modelName}.js', 'r')
    content = f.read()
    f.close()
    return templates.TemplateResponse("model.html", {
        "request": request,
        "modelName": modelName,
        "modelMode": model.modelMode,
        "stopTime": model.stopTime,
        "dataSets": json.dumps(model.dataSets),
        "stepSize": model.stepSize,
        "interval": model.interval,
        "contentOfJS": content
    })

#TODO: dorobit validaciu suboru či to je fmu subor
@app.post("/uploadfile/")
async def create_upload_file(uploaded_file: UploadFile = File(...)):
    file_name = uploaded_file.filename[:-4]
    if(os.path.isdir(f"/var/www/fastapi/assets/models/{file_name}") == True):
        return {"Model with same name already exist. Please change name of uploaded model."}
    file_location = f"Bodylight.js-FMU-Compiler/input/{uploaded_file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(uploaded_file.file.read())
    file_path = f"/var/www/fastapi/Bodylight.js-FMU-Compiler/output/{file_name}.zip"
    timeout = 5   # [seconds]
    timeout_start = time.time()
    while time.time() < timeout_start + timeout:
        if os.path.isfile(file_path):
            break
        time.sleep(1)
    if(os.path.isfile(file_path)):
        os.system(f"unzip /var/www/fastapi/Bodylight.js-FMU-Compiler/output/{file_name}.zip -d /var/www/fastapi/assets/models/{file_name}")
        os.system(f"cp -R /var/www/fastapi/assets/models/{file_name}/{file_name}.xml /var/www/fastapi/assets/models_xml")
        return {"Success :)"}
    else:
        #TODO: dorobit API ktora len prida file potom ako sa convertuje do js v pripade, ze sa dlho convertuje subor
        return {"File was not uploaded automatically because it takes longer to convert fmu file to js. Please wait a little longer and use other API that will just upload file"}
    return {"Other error"}

@app.post("/uploadfmu/")
async def give_zip(uploaded_fmu: UploadFile = File(...)):
    file_name = uploaded_fmu.filename[:-4]
    if(os.path.isdir(f"/var/www/fastapi/assets/models/{file_name}") == True):
        return {"Model with same name already exist. Please change name of uploaded model."}
    file_location = f"Bodylight.js-FMU-Compiler/input/{uploaded_fmu.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(uploaded_fmu.file.read())
    file_path = f"/var/www/fastapi/Bodylight.js-FMU-Compiler/output/{file_name}.zip"
    timeout = 10   # [seconds]
    timeout_start = time.time()
    while time.time() < timeout_start + timeout:
        if os.path.isfile(file_path):
            break
        time.sleep(1)
    if(os.path.isfile(file_path)):
        os.system(f"unzip /var/www/fastapi/Bodylight.js-FMU-Compiler/output/{file_name}.zip -d /var/www/fastapi/assets/models/{file_name}")
        os.system(f"cp -R /var/www/fastapi/assets/models/{file_name}/{file_name}.xml /var/www/fastapi/assets/models_xml")
        return FileResponse(path=file_path, filename=file_name + ".zip", media_type="multipart/form-data")
    else:
        return {"File was not returned"}

@app.get("/downloadModel/{modelName}")
async def returnFile(modelName: str):
    if (os.path.isfile(f"/var/www/fastapi3/assets/models/{modelName}/{modelName}.js") == False):
        return {"Model does not exist"}
    if (os.path.isfile(f"/var/www/fastapi3/assets/models/{modelName}/{modelName}.zip") == True):
        file_path = f"/var/www/fastapi3/assets/models/{modelName}/{modelName}.zip"
    else:
        os.system(f"zip -r /var/www/fastapi3/assets/models/{modelName}/{modelName}.zip /var/www/fastapi3/assets/models/{modelName}")
        file_path = f"/var/www/fastapi3/assets/models/{modelName}/{modelName}.zip"

    return FileResponse(path=file_path, filename=modelName + ".zip", media_type="multipart/form-data")

@app.post("/returnFile/")
async def returnFile(uploaded_fmu: UploadFile = File(...)):
    #some_file_path = "BouncingBall2.fmu"
    #return FileResponse(some_file_path, media_type='application/octet-stream', filename="BouncingBall2.fmu")
    #headers = {'Content-Disposition': 'attachment; filename="BouncingBall2.fmu"'}
    #return FileResponse(some_file_path, headers=headers)
    return FileResponse(path=uploaded_fmu.filename, filename=uploaded_fmu.filename, media_type="multipart/form-data")

#TODO: pridat vyskakovacie modal okno k buttonu ci naozaj chce uzivatel vymazat model
@app.get("/model/remove/{modelName}")
async def remove_model(modelName: str):
    if(os.path.isfile(f"/var/www/fastapi/assets/models_xml/{modelName}.xml") == False):
        return {"Model does not exist"}

    os.system(f"rm -f /var/www/fastapi/Bodylight.js-FMU-Compiler/output/{modelName}.log")
    if(os.path.isfile(f"/var/www/fastapi/Bodylight.js-FMU-Compiler/output/{modelName}.log")):
        return {"Failed deleting log file in output file of compiler"}

    os.system(f"rm -f /var/www/fastapi/Bodylight.js-FMU-Compiler/output/{modelName}.zip")
    if(os.path.isfile(f"/var/www/fastapi/Bodylight.js-FMU-Compiler/output/{modelName}.zip")):
        return {"Failed deleting zip file in output directory of compiler"}

    os.system(f"rm -r /var/www/fastapi/assets/models/{modelName}")
    if(os.path.isdir(f"/var/www/fastapi/assets/models/{modelName}")):
        return {"Failed deleting directory of model"}

    os.system(f"rm /var/www/fastapi/assets/models_xml/{modelName}.xml")
    if(os.path.isfile(f"var/www/fastapi/assets/models_xml/{modelName}.xml")):
        return {"Failed deleting xml of model"}

    return {"success": True}

@app.post("/fmu/modelRun", tags=["FMU"])
async def fmu_model_run(model: Model = Depends(),file: UploadFile = File(...)):
    outputValues = None
    if model.outputValues != None:
        outputValues = model.outputValues.split(",")
        for i, value in enumerate(outputValues): #if somebody writes values with whitespace after ","
            outputValues[i] = ''.join(value.split())

    startValues_dict = {}
    if model.startValues != None:
        startValues = model.startValues.split(",")
        for i, value in enumerate(startValues): #if somebody writes values with whitespace
            startValues[i] = ''.join(value.split())
            values = startValues[i].split("=")
            startValues_dict.update({values[0]: values[1]})

    try:
        result = simulate_fmu(file.filename, output=outputValues, start_values=startValues_dict , start_time=model.startTime, stop_time=model.stopTime, step_size=model.stepSize, solver=model.solver, relative_tolerance=model.relative_tolerance)
    except Exception as e:
        return {"Error from simulate_fmu:": e}
    fmu_result = np.array(result) # je to treba zmenit z numpy na str aby sa to dalo poslat
    keys = fmu_result.dtype.names

    #toto je rozdelene pre kazdu premennu zvlast do array napr: time: [0,1,2,...], h: [1,2,3,...], v: [2,3,4,...]
    final_result = {}
    for key in keys:
        final_result.update({key: []})
        values = np.array(result[key])
        for value in values:
            final_result[key].append(value)

    # toto ukazuje v tvare napr: time,h,v: [0,1,2], [0.1,1.1,2.1], ...
    title = ""
    for i, key in enumerate(keys):
        if i == len(keys) - 1:
            title += key
        else:
            title += key + ","
    final_result2 = {title: []}
    for value in fmu_result:
        final_result2[title].append(tuple(value))

    final_result3 = []
    for value in fmu_result:
        temp_dict = {}
        for i, key in enumerate(keys):
            temp_dict.update({key: value[i]})
        final_result3.append(temp_dict)

    return final_result3

@app.post("/fmu/modelInfo", tags=["FMU"])
async def fmu_model_info(uploaded_fmu: UploadFile = File(...)):
    md = read_model_description(uploaded_fmu.filename, validate=False)
    platforms = fmpy.supported_platforms(uploaded_fmu.filename)

    fmi_types = []
    if md.modelExchange is not None:
        fmi_types.append('Model Exchange')
    if md.coSimulation is not None:
        fmi_types.append('Co-Simulation')

    ex = md.defaultExperiment

    variables = []
    for v in md.modelVariables:
        start = str(v.start) if v.start is not None else ''
        unit = v.declaredType.unit if v.declaredType else v.unit
        variables.append({
            "Name": v.name,
            "Causality": v.causality,
            "Start": start,
            "Unit": unit,
            "Description": v.description
        })

    model_info = {
        "Model Info": {
            "FMI Version": md.fmiVersion,
            "FMI Type": ', '.join(fmi_types),
            "Model Name": md.modelName,
            "Description": md.description,
            "Platforms": ', '.join(platforms),
            "Continuous States": md.numberOfContinuousStates,
            "Event Indicators": md.numberOfEventIndicators,
            "Number of variables": len(md.modelVariables),
            "Generation Tool": md.generationTool,
            "Generation Date": md.generationDateAndTime
        },
        "Default Experiment": {
            "Start Time": ex.startTime,
            "Stop Time": ex.stopTime,
            "Tolerance": ex.tolerance,
            "Step Size": ex.stepSize
        },
        "Variables": variables
    }
    return {"model": model_info}

@app.post("/matlab/uploadmodel/")
async def create_upload_file(uploaded_file: UploadFile = File(...)):
    file_location = f"/home/rokulus/Desktop/{uploaded_file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(uploaded_file.file.read())

    engs = matlab.engine.find_matlab()
    if not engs:
       eng = matlab.engine.start_matlab()
    else:
       eng = matlab.engine.connect_matlab(engs[0])


    #eng.open_system('/home/rokulus/Desktop/model.slx', nargout=0)
    eng.workspace['model_path'] = f"/home/rokulus/Desktop/{uploaded_file.filename}"
    eng.workspace['model'] = f"{uploaded_file.filename}"
    eng.eval('model = erase(model,".slx")',nargout=0)
    #eng.open_system(model_path, nargout=0)
    eng.eval('open_system(model_path)',nargout=0)
    #eng.sim('model')
    eng.eval('sim(model)',nargout=0)
    eng.eval('x = ans.y;',nargout=0)
    x = eng.workspace['x']

    c = [[] for _ in range(len(x[0]))]
    for i in range(len(x[0])):
        for j in range(len(x)):
            c[i].append(x[j][i])

    return {"success" : c}


htmlWebSocket = """
<!DOCTYPE html>
<html>
    <head>
        <title>Websocket</title>
    </head>
    <body>
        <h1>WebSocket</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://147.175.121.226/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

app.lock = threading.Lock()

@app.get("/websocket")
def start_job(some_args):
    if app.lock.acquire(False):
        th = threading.Thread(target=websocket_endpoint,kwargs=some_args)
        th.start()
        return HTMLResponse(htmlWebSocket)
    else:
        raise HTTPException(status_code=400,detail="Job already running.")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, background_tasks: BackgroundTasks):
    await websocket.accept()
    engs = matlab.engine.find_matlab()
    if not engs:
        eng = matlab.engine.start_matlab()
    else:
        eng = matlab.engine.connect_matlab(engs[0])

    try:
        data = await websocket.receive_text()
        eng.set_param('model/Gain','Gain', str(data), nargout=0)
        eng.set_param('model','SimulationCommand', 'start', nargout=0)
        while float(eng.get_param('model','SimulationTime')) <= float(eng.get_param('model','StopTime')) and eng.get_param('model', 'SimulationStatus') != 'stopped':
            eng.eval('get_param("model","SimulationTime")', nargout=0)
            eng.eval('rto = get_param("model/Gain", "RuntimeObject")', nargout=0)
            eng.eval('real_time_data = rto.OutputPort(1).Data', nargout=0)
            real_time_data = eng.workspace['real_time_data']
            await push_data(websocket, real_time_data)
    except WebSocketDisconnect:
        app.lock.release()


app.lock = False

@app.get("/websocket")
async def get_websocket():
    if not app.lock:
        app.lock = True
        return HTMLResponse(htmlWebSocket)
    else:
        raise HTTPException(status_code=404, detail="Websocket is already running, please wait")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, background_tasks: BackgroundTasks):
    await websocket.accept()
    engs = matlab.engine.find_matlab()
    if not engs:
        eng = matlab.engine.start_matlab()
    else:
        eng = matlab.engine.connect_matlab(engs[0])

    try:
        data = await websocket.receive_text()
        eng.set_param('model/Gain','Gain', str(data), nargout=0)
        eng.set_param('model','SimulationCommand', 'start', nargout=0)
        while float(eng.get_param('model','SimulationTime')) <= float(eng.get_param('model','StopTime')) and eng.get_param('model', 'SimulationStatus') != 'stopped':
            eng.eval('get_param("model","SimulationTime")', nargout=0)
            eng.eval('rto = get_param("model/Gain", "RuntimeObject")', nargout=0)
            eng.eval('real_time_data = rto.OutputPort(1).Data', nargout=0)
            real_time_data = eng.workspace['real_time_data']
            await push_data(websocket, real_time_data)
    except WebSocketDisconnect:
        app.lock = False

@asyncio.coroutine
def push_data(websocket, data):
        yield from websocket.send_text(f"Data: {data}")
        yield from asyncio.sleep(0)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    engs = matlab.engine.find_matlab()
    if not engs:
       eng = matlab.engine.start_matlab()
    else:
       eng = matlab.engine.connect_matlab(engs[0])

    while True:
        try:
            data = await websocket.receive_text()
            eng.set_param('model/Gain','Gain', str(data), nargout=0)
            eng.set_param('model','SimulationCommand', 'start', nargout=0)
            while float(eng.get_param('model','SimulationTime')) <= float(eng.get_param('model','StopTime')) and eng.get_param('model', 'SimulationStatus') != 'stopped':
                eng.eval('get_param("model","SimulationTime")', nargout=0)
                eng.eval('rto = get_param("model/Gain", "RuntimeObject")', nargout=0)
                eng.eval('real_time_data = rto.OutputPort(1).Data', nargout=0)
                real_time_data = eng.workspace['real_time_data']
                await push_data(websocket, real_time_data)

        except Exception as e:
            print('Exception websocket ERROR:', e)
            break