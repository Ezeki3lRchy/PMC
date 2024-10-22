% create an instance from class_model
model = ModelUtil.create('Model');

% open GUI client
mphlaunch("Model");



model.param.set('mh', '1[mm]', 'Maximum element size');
model.param.set('hfbc', '1[mm]', 'HeatFlux');
% Geometry
comp1 = model.component.create('comp1', true); % comp1 = model.component.comp1
geom1 = comp1.geom.create('geom1', 3);
import1 = geom1.create('import1','Import');
import1.set('filename','E:\Postgraduate\ansys\heatsink.STEP');
mphrun(model,'geom1');


% show the model
% mphgeom(model,'geom1');

sel1 = comp1.selection.create('sel1');
sel1.geom('geom1',2);
sel1.set([1 2 4 5]);
sel1.label('insulation');

sel2 = comp1.selection.create('sel2');
sel2.geom('geom1',2);
sel2.set(6);
sel2.label('heatflux');

sel3 = comp1.selection.create('sel3');
sel3.geom('geom1',2);
sel3.set(3);
sel3.label('radiation BC');

sel4 = comp1.selection.create('sel4');
sel4.geom('geom1',3);
sel4.set(1);
sel4.label('body');

%
mat_PM1000 = comp1.material.create('mat_PM1000');
mat_PM1000.materialModel('def').set('heatcapacity', '890[J/(kg*K)]');
mat_PM1000.materialModel('def').set('density', '8240[kg/m^3]');
mat_PM1000.materialModel('def').set('thermalconductivity', {'42[W/(m*K)]'});
% 1200 Celsius
mat_PM1000.label('PM1000');

comp1.material('mat_PM1000').selection.named('sel4');

% Physics Interface
ht_PM1000 = comp1.physics.create('ht_PM1000', 'HeatTransfer','geom1');

hf_BC = ht_PM1000.feature.create('hf_BC', 'HeatFluxBoundary', 2); % 2= 2 dimension
hf_BC.set('HeatFluxType', 'GeneralInwardHeatFlux'); 
hf_BC.selection.set(6);
hf_BC.set('q0_input', '5e3');


hf_rad = ht_PM1000.feature.create('hf_rad', 'HeatFluxBoundary', 2);
hf_rad.set('HeatFluxType', 'GeneralInwardHeatFlux'); 
hf_rad.selection.set(3);
hf_rad.label('rad');

% Mesh
mesh1 = comp1.mesh.create('mesh1');
size = mesh1.feature('size');
size.set('hmax', 'mh');
size.set('hmin', 'mh-mh/3');
size.set('hcurve', '0.2');
mesh1.feature.create('ftet', 'FreeTet');
mphrun(model,'mesh');

% Study
std = model.study.create('std');
std.feature.create('stat', 'Time Dependent');
mphrun(model,'study');

% Plotting The Results
tags = mphtags(model, 'result'); %  get the list of the plot group tags available under the result node
% pgtag = plot group tag
feattags = mphtags(model.result(tags{1})); % the tag of the plot feature in the first plot group
% feattage= feature tag or ftag

surf = model.result(tags{1}).feature(feattags{1});
surf.set('rangecoloractive', 'on');
surf.set('rangecolormin', '280');
surf.set('rangecolormax', '350');


mphsave(model,'C:\project_IHCP\IHCP_flight_test.mph')
