import matlab.engine
import os
import time

# init
def matlab_init(i_path):
    # COMSOL and MATLAB
    # NOTE: have comsolstartup.m file, should have the right path and matlab.engine.shareEngine
    os.startfile(i_path)  # must launch it by .Ink for launch option 'matlab'

    # waiting
    time.sleep(13)

    # link to python
    matlab_sessions = matlab.engine.find_matlab()
    matlab_eng = None
    if matlab_sessions:
        matlab_eng = matlab.engine.connect_matlab(matlab_sessions[0])
    else:
        max_retries = 5
        retry_delay = 3  # delta s
        for _ in range(max_retries):
            time.sleep(retry_delay)
            matlab_sessions = matlab.engine.find_matlab()
            if matlab_sessions:
                matlab_eng = matlab.engine.connect_matlab(matlab_sessions[0])
                matlab_eng.eval("disp('Completed')", nargout=0)
                break
        else:
            print("Failed to connect to MATLAB session after retries.")
    return matlab_eng