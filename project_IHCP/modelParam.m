function modelParam(model_path,env_path,save_path)
% The function first creates a file and then sets the header of the output file format.
% env_path = 'E:\Postgraduate\Matlab\project_IHCP';

% filepath = 'E:\Postgraduate\Matlab\project_IHCP';



% When running a large number of iterations, the model history can be disabled 
% to prevent the memory usage from increasing with each iteration due to
% the model history stored in the model.  

 % Lower bound of the interval
 % Upper bound of the interval
 % Number of random numbers to generate
% randomIntegers = randi([lower_bound, upper_bound], N, 1); 

for i = 1: N
% Para
model = mphopen(model_path);
A = randomIntegers(i);
offset = A ;
model.hist.disable;
model.param.set('A',A);
model.param.set('offset',offset);
% Run
mphrun(model,'study'); 
% Save model
modelName = fullfile(save_path,[ ...
                 'Type=','sin',...
                '_A=',num2str(A),...
                '_offset=',num2str(offset),...
                '.mph']);
mphsave(model,modelName);


input_path =  fullfile(env_path,'input');
output_path = fullfile(env_path,'output');
casename = ['A_',num2str(A)];
mkdir(fullfile(input_path,casename));
mkdir(fullfile(output_path,casename));
                 % Exporting Rear Temperature Results as Image
model.result.export('anim1').set('imagefilename',  fullfile(input_path,casename,'input.png'));
                 % Exporting Heat flux Results as Image
model.result.export('anim3').set('imagefilename',  fullfile(output_path,casename,'output.png'));

model.result().export("anim1").run();
model.result().export("anim3").run();
end
end

% If COMSOL with MATLAB is not already running, start it now and load the busbar model from the application library:
% model = mphopen('busbar');
% Run the function and substitute 'filepath' with the directory of your choice:
% modelParam(model,'filepath')