import matlab.engine
import os
import random
import subprocess
import time

# env_var_COMSOL with matlab
SHORTCUT_PATH = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\COMSOL Multiphysics 6.3"
SHORTCUT_NAME = "COMSOL Multiphysics 6.3 with MATLAB.lnk"
FULL_PATH = os.path.join(SHORTCUT_PATH, SHORTCUT_NAME)

# env_var_model and parameter
material = "test"  # pm1000 / sio2 / ptrh
parameter_type = "var_p_mu"  # constant or sin

SAVE_PATH = os.path.normpath(f'D:\\32_MoviLSTM\\Argon_GEC_CCP\\dataset_{material}_{parameter_type}')

#input_model_path = os.path.normpath(f'C:\\project_IHCP\\IHCP_flight_{material}_{heatflux_type}.mph')
INPUT_MPH_PATH = os.path.normpath(f'D:\\32_MoviLSTM\\Argon_GEC_CCP\\argon_gec_ccp.mph')
SAVE_MPH_PATH = os.path.normpath(f'D:\\32_MoviLSTM\\Argon_GEC_CCP\\cas')



# init
def matlab_init(i_path):
    # COMSOL and MATLAB
    # NOTE: have comsolstartup.m file, should have the right path and matlab.engine.shareEngine
    os.startfile(i_path)  # must launch it by .Ink for launch option 'matlab'

    # waiting
    time.sleep(5)

    # link to python
    matlab_sessions = matlab.engine.find_matlab()
    matlab_eng = None
    if matlab_sessions:
        matlab_eng = matlab.engine.connect_matlab(matlab_sessions[0])
    else:
        max_retries = 20
        retry_delay = 3  # delta s
        for _ in range(max_retries):
            time.sleep(retry_delay)
            matlab_sessions = matlab.engine.find_matlab()   
            if matlab_sessions:
                matlab_eng = matlab.engine.connect_matlab(matlab_sessions[0])
                matlab_eng.eval("disp('Completed')", nargout=0)  # type: ignore
                break
        else:
            print("Failed to connect to MATLAB session after retries.")
    return matlab_eng


eng = matlab_init(FULL_PATH)

#  test
if eng is not None:
    try:
        eng.eval("a = 1:5", nargout=0) # type: ignore
    except Exception as e:
        print(f"An error occurred: {e}")
else:
    print("Failed to initialize MATLAB engine.")

# random number
num_elements = 500
min_value = 0.05
max_value = 0.3
random_numbers = [random.uniform(min_value, max_value) for _ in range(num_elements)]
kv_values = [x / 1000 for x in random_numbers]
counter = 0




for i in random_numbers:

    # matlab TUI # 
    eng.eval(f""" 
             
        model = mphload('{INPUT_MPH_PATH}'); % load the model

        % set the parameters
        A = {i};
        offset = {i};
        model.hist.disable;
        model.param.set('A', A);
        model.param.set('offset', offset);
        model.param.set('pgas', '{i}[Torr]');


        % run the model
        mphrun(model, 'std1');
        mphrun(model, 'std2');
        
        % save the model
        modelName = fullfile('{SAVE_MPH_PATH}', [ ...
                    'material=', '{material} ' ,...
                    '{i}_',...
                    'Type=', '{parameter_type}',...
                    '_A=', num2str(A),...
                    '_offset=', num2str(offset),...
                    '.mph']);
        
        mphsave(model,modelName);
        input_path =  fullfile('{SAVE_PATH}', 'input');
        output_path = fullfile('{SAVE_PATH}', 'output');
        casename = ['{counter}', 'A_', num2str(A)];
        mkdir(fullfile(input_path, casename));
        mkdir(fullfile(output_path, casename));

                     % Exporting Rear Temperature Results as Image
        
                     % Exporting Heat flux Results as Image
        model.result.export('anim2').set('imagefilename',  fullfile(input_path,casename, 'input.png'));            
        model.result.export('anim3').set('imagefilename',  fullfile(output_path,casename, 'output.png'));

        
        model.result().export("anim2").run(); 
        model.result().export("anim3").run();
        
        """, nargout=0) 
    counter += 1
    if counter % 50 == 0:
        eng.exit()
        processes_to_kill = ['MATLAB.exe', 'comsolmphserver.exe']  # 'comsoldocserver.exe'
        [subprocess.run(['taskkill', '/F', '/IM', process_name]) for process_name in processes_to_kill]
        eng = matlab_init(FULL_PATH)

'''
nargout=0: This means you expect no output arguments from the MATLAB function. 
The function is called, but any outputs that it would normally return are ignored. 
This is useful when you are calling MATLAB functions for their side effects (like plotting) 
and do not need any values returned.

nargout=1: This means you expect the MATLAB function to return a single output argument, 
which will be captured by a Python variable.

nargout=N (where N is an integer greater than 1): This means you expect 
the MATLAB function to return N output arguments. The Python function call will return a tuple containing N elements,
 each corresponding to one of the MATLAB function's output arguments.
'''
