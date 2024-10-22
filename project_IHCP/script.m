% Script

% If COMSOL with MATLAB is not already running, start it now and load the busbar model from the application library:
% model = mphopen('busbar');
% Run the function and substitute 'filepath' with the directory of your choice:
% modelParam(model,'filepath')

% env_var
env_path = 'C:\project_IHCP\dataset';
model_path = 'C:\project_IHCP\IHCPprototype.mph';

model = mphload('C:\project_IHCP\IHCPprototype.mph');
mphlaunch("Model"); % Client
% mphnavigator


% function modelParam(model,env_path, lower_bound, upper_bound, N)
modelParam(model_path,env_path, 2e6, 5e6, 500); % why 104 error? 210 error; server is missing;1e5 ;2e6