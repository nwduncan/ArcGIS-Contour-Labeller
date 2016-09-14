# ArcGIS Contour Labeller v1.1
An ArcGIS python add-in that allows for simple contour labelling.


## Install
1. Clone the repository
2. Run makeaddin.py. 
3. Install the resulting .esriaddin file.


## How to use
1. The toolbar can be found in Customize > Toolbars > Contour Labeller
2. Add your contour line feature class to your mxd and select it from the 'Contour Layer' drop-down
3. Select the attribute field which contains the elevation data in your contours layer from the 'Height Field' drop-down
4. Use the 'Draw Labels' tool to begin drawing your label lines. The 'rotation_angle' field value for each label will be determined by the angle at which you draw the lines
5. If you make a mistake you can reset the tool by clicking on the 'Reset Label Lines' button
6. When you're ready to create the labels click on the 'Create Labels Layer' button


## Tips
- When labelling use the Maplex labelling engine with the position of the label set to 'Center' and use 'Rotate by attribute' with the rotation field selected and 'Rotation Type' set to 'Arithmetic'.
- Resulting point layers are saved in your scratch workspace. If you want to change your scratch workspace location you'll find it in the 'Environments...' > 'Workspace' under the 'Geoprocessing' menubar. I recommend moving the resulting layers to a more permanent location to avoid losing data.