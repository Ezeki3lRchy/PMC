% This is the startup script called by COMSOL Multiphysics with MATLAB
%
% See also: mphopen, mphversion

% Copyright 2011-2022 COMSOL

% Write some general information in the Command Window
[~,~,v2] = mphversion;
fprintf('\nStarting COMSOL Multiphysics LiveLink(TM) for MATLAB(R) - %s.\n\n', v2)

if isempty(which('narginchk'))
    warning('This version of MATLAB is not supported and lacks the function ''narginchk''')
end

% Try to find the user's startup file. Such file must have the
% name "comsolstartup.m" and be placed in the user's home
% directory or on the Matlab path.
if ispc
    userdir = getenv('userprofile');
else
    userdir = getenv('HOME');
end
curdir = pwd;
startpath = fullfile(userdir, 'comsolstartup.m');
fprintf('Checking for additional startup script (comsolstartup.m)\n');
fprintf('  in: %s\n', userdir);
flag = false;
if exist(startpath, 'file')==2
    fprintf('\nRunning: %s\n\n', startpath)
    flag = true;
    cd(userdir)
    saveddir = pwd;
    evalin('base', 'comsolstartup')
    if strcmp(saveddir, pwd)
        cd(curdir)
    end
end

if flag==false
    fprintf('\nChecking for startup script on the MATLAB path\n');
    startpath = which('comsolstartup.m');
    if length(startpath)
        fprintf('Running: %s\n\n', startpath)
        p = fileparts(startpath);
        cd(p)
        saveddir = pwd;
        evalin('base', 'comsolstartup')
        if strcmp(saveddir, pwd)
            cd(curdir)
        end
    end
end

pause(1)
hassli = which('\sli\Contents.m');
if desktop('-inuse')
    if isempty(hassli)
        msg1 = 'Type <a href="matlab:help mli">help mli</a> for more information';
    else
        msg1 = 'Type <a href="matlab:help mli">help mli</a> and <a href="matlab:help sli">help sli</a> for more information';
    end
    msg2 = 'Type <a href="matlab:mphapplicationlibraries">mphapplicationlibraries</a> to open the Application Library';
else
    if isempty(hassli)        
        msg1 = 'Type help mli for more information';
    else
        msg1 = 'Type help mli and help sli for more information';
    end
    msg2 = 'Type mphapplicationlibraries to open the Application Library';
end

import com.comsol.model.util.*
if ModelUtilInternal.isApplicationServer 
    fprintf('\n\n%s\n\n', msg1);
else
    fprintf('\n\n%s\n\n%s\n\n', msg1, msg2);
end

clear hassli v2 flag startpath userdir curdir saveddir comsolpwd ans msg1 msg2
