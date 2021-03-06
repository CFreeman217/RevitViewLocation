"""
PROTOTYPE VERSION 0.01
< HOLD 'ALT' AND CLICK TO VIEW SOURCE CODE AND KNOWN BUGS >
"""
"""

Design a gas piping system with the 'System Type' parameter set containing
the word 'gas' and it becomes a target element for sizing. All fixture families 
connected to the system must use connectors with the 'Flow' parameter set in 
MBH. Find the totaldeveloped length of the system in feet by summing the pipe 
lengths of the longest branch from meter to fixture. Select the pipes you want 
to size, then click this tool. Brings up a dialog to select gas system parameters 
and enter total final developed length of system in feet. 

If the 'Change pipe geometry' checkbox is checked, the script will automatically
size the gas pipes selected

This tool was developed with the 2018.1 API from revitapidocs.com.

Thanks to freepik at flaticons.com for providing the plumbing icon design.
Thanks to smashicon at flaticons.com for providing the gas system sizing design.

"""
"""
This script is an extension for the pyrevit addin to run on 
Autodesk Revit 2018 produced for TK Architects of Kansas City, MO. 
Written by Clay Freeman in collaboration with Larry Tatum.

The script filters out the selected elements down to only gas system pipes,
collects the diameter and flow and uses the equations in the 2015 International
Fuel and Gas Code manual to determine appropriate pipe diameters for the flow
rates given. 

KNOWN ISSUES:

2. Develop a better solution for catching strings as input for the TDL.
3. Clicking the x in the corner brings up an error. Find a better way to 
    terminate the script from the GUI.
4. Collecting the parameters using pipe_section class is a waste of energy 
    and resources. Rearrange the main function to actually sit inside proper 
    functions and not waste time gathering unnessecary
"""
import clr # Adds .NET library functionality
import sys # System functions to interact with the interpreeter
import collections # Useful tools for generating and accessing groups of elements
import Autodesk 
import Autodesk.Revit.DB as DB # Allows access to the DB namespace. Lots of tools.
    # See revitapidocs.com

# Import DocumentManager and TransactionManager
# clr.AddReference("RevitServices")
# import RevitServices
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

# Allows access to element geometry
clr.AddReference("ProtoGeometry")
from Autodesk.DesignScript.Geometry import *

# Gets nessecary resources for generating the user input window triggered on tool
#   click.
clr.AddReference("PresentationFramework")
from scriptutils.userinput import WPFWindow
from System.Windows import Window, Application
from System.Windows.Controls import TextBox

# Generate references for the active window and application.
app = __revit__.Application
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

# Create a class to hold instances of each pipe section element.
class pipe_section:
    # Script runs when an instance is created
    def __init__(self):
        # We can define instance variables later as we need them
        return

# A class that holds the GUI user input data.
class inputData:
    # By defining these instance variables in the GUIgenerator class,
    # it is much easier to add buttons or functionality by just changing
    # that line in the script.
    def __init__(self):
        return

# The GUI generator.
class GUIgenerator(WPFWindow):
    # Calling the class and feeding it a window. 
    # This command generates the window popup
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)
        self.DataContext = self

    # This function is called when the button is clicked.
    # Gathers information about the state of the gui.
    def sizeSystem_button(self, sender, e):       
        inputData.sys_length = self.TDL_textBox.Text
        inputData.press_drop_sel = self.presDrop_comboBox.SelectedValue.ToString()
        inputData.inlet_press_sel = self.inPressure_comboBox.SelectedValue.ToString()
        inputData.pressureState = self.HP_radioButton.IsChecked
        inputData.geometry = self.geo_ckbx.IsChecked
        inputData.closeAfter = self.cl_ckbx.IsChecked
        inputData.natGas = self.NG_radioButton.IsChecked
    
    # Trying to fix the error called when the x is clicked in the upper right
    # corner of the window.


# Gathers parameters and returns the dictionary, stolen from example code on 
# the apidocs website. Computationally expensive. Eliminate this.
def collect_params(param_element):
    """
    Collects parameters of the provided element.
    Args:
        param_element: Element that holds the parameters.
    Returns:
        Returns a dictionary, with parameters.
    """

    parameters = param_element.Parameters
    param_dict = collections.defaultdict(list)

    for param in parameters:
        param_dict[param.Definition.Name].append(param.StorageType.ToString().split(".")[-1])
        param_dict[param.Definition.Name].append(param.HasValue)

        param_value = None
        if param.HasValue:
            if param.StorageType.ToString() == "ElementId":
                param_value = param.AsElementId().IntegerValue
            elif param.StorageType.ToString() == "Integer":
                param_value = param.AsInteger()
            elif param.StorageType.ToString() == "Double":
                param_value = param.AsDouble()
            elif param.StorageType.ToString() == "String":
                param_value = param.AsString()
        param_dict[param.Definition.Name].append(str(param_value))

    return param_dict

def get_piping_system_type(param_name):
    # Accesses the ID associated with the built-in paramater "System Classification" 
    # See RevitApiDocs: BuiltInParameter Enumeration
    param_id = DB.ElementId(DB.BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM)
    # The filter needs the ID of the parameter we are searching for:
    # See RevitApiDocs: FilterableValueProvider Class
    param_prov = DB.ParameterValueProvider(param_id)
    # The filter also takes a rule evaluation
    # See RevitApiDocs: FilterStringRuleEvaluator Look at the inheritance Heirarchy
    # to get an idea of what options this has.
    filter_rule = DB.FilterStringContains()
    # This line directly translates from the C# example provided in the documentation
    # to the python equivalent. See RevitApiDocs: ElementParameterFilter Class
    case_sensitive = False
    param_filter = DB.FilterStringRule(param_prov, \
                                            filter_rule, \
                                            param_name, \
                                            case_sensitive)
    # Assigns our filter to the element parameter filter so it fits into the 
    # 'WherePasses' method
    element_filter = DB.ElementParameterFilter(param_filter)
    # Collect a list of items eligible to get picked by the filter.
    # I found OST_PipeCurves from a combination of looking over the built in categories and
    collected_elements = DB.FilteredElementCollector(doc) \
            .OfCategory(DB.BuiltInCategory.OST_PipeCurves) \
            .WherePasses(element_filter) \
            .ToElements()

    return collected_elements

def round_PipeSize(size):
	# Function accepts decimal calculated value for IFGC pipe sizing and
	# returns the next larger available pipe from commonly available sizes.
    inner_Diam = ('0.824',\
                    '1.049',\
                    '1.380',\
                    '1.610',\
                    '2.067',\
                    '2.469',\
                    '3.068',\
                    '4.026',\
                    '6.065',\
                    '7.981')
    
    avail_Sizes = ('0.75',\
                    '1.00',\
                    '1.25',\
                    '1.50',\
                    '2.00',\
                    '2.50',\
                    '3.00',\
                    '4.00',\
                    '6.00',\
                    '8.00')
    if size == 0:
        next
    i = 0
    for option in inner_Diam:
        if size < float(option):
            return (float(avail_Sizes[i])/12)
        else:    
            i += 1

def size_HPPipe(gas_load, tot_Length, press_in, nat_gas):
    # Calculate the IFGC high pressure pipe size from the equation:
    # 
	# D =                Q^(0.381)
	#     ---------------------------------------
	#             [ |p_2^2 - p_1^2| * Y ]^(0.206)
    #     18.93 * [---------------------]
    #             [        Cr * L       ]
    #
    # Where: Q = Gas Load
    # 
    if press_in == 2:
        press_drop = 1
    elif press_in == 3:
        press_drop = 2
    elif press_in == 5:
        press_drop = 3.5
    else:
        press_drop = "High Pressure Select Error"

    p_1 = press_in + 14.7
    p_2 = (press_in - press_drop) + 14.7
    
    # Natural Gas Cr and Y: 
    if nat_gas:
        Cr = 0.6094
        Y = 0.9992
    else: # Propane Cr and Y:
        Cr = 1.2462
        Y = 0.9910
    
    num = (gas_load*448.833)**(0.381)

    bracket = ((abs(p_2**2 - p_1**2)*Y) / (Cr * tot_Length))**(0.206)
    den = 18.93*bracket
    diam = num / den
    return diam

def size_LPPipe(gas_load, tot_length, press_drop, nat_gas):
	# Calculate the IFGC low pressure pipe size from the equation:
	#
	# D =         Q^(0.381)
	#     ------------------------  
	#             [   d_H  ]^0.206  
    #     19.17 * [--------]
    #             [ Cr * L ]
    #
    # Where: Q = Gas Load
    #        d_H = Pressure Drop

    if nat_gas:
        # Natural Gas
        Cr = 0.6094
    else:
        # Propane
        Cr = 1.2462


    num = (gas_load*448.833)**(0.381)
    bracket = ((press_drop)/(Cr*tot_length))**(0.206)
    den = 19.17*bracket
    
    diam = num / den
    return diam

def main():
    input_params = GUIgenerator('gaspipesize.xaml').ShowDialog()
    print("\nGUI INPUT DATA RECEIVED... ")
    target_elements = get_piping_system_type("GAS")
    target_elIds = []
    for element in target_elements:
        target_elIds.append(element.Id)

    selected_elIds = []  
    selected_elements = [doc.GetElement(elId) for elId in uidoc.Selection.GetElementIds()]

    for element in selected_elements:
        selected_elIds.append(element.Id)

    selected_pipes = set(target_elIds).intersection(selected_elIds)
    print("\nEvaluating  " + str(len(selected_pipes)) + "  Selected Gas Pipes...")
    changeCount = 0
    t = DB.Transaction(doc,"ChangePipeDiameters")

    t.Start()
    for pipeId in selected_pipes:
        pipe_params = collect_params(doc.GetElement(pipeId))
        pipe_section.elementId = pipeId
        pipe_section.pipeFlow = float(pipe_params['Flow'][2])
        pipe_section.diameterRead = round(float(pipe_params ['Diameter'][2]),11)
        if inputData.pressureState:
            # High Pressure Pipe
            pipe_section.diameterCalc = size_HPPipe(float(pipe_section.pipeFlow), \
                                                float(inputData.sys_length), \
                                                int(inputData.inlet_press_sel[0]), \
                                                bool(inputData.natGas))
            print("Calculated Diameter:  " + str(pipe_section.diameterCalc) + " in.")
        else:
            pipe_section.diameterCalc = size_LPPipe(float(pipe_section.pipeFlow), \
                                                float(inputData.sys_length), \
                                                float(inputData.press_drop_sel[:3]), \
                                                bool(inputData.natGas))
        pipe_section.diameterNew = round_PipeSize(pipe_section.diameterCalc)
        if pipe_section.diameterNew != None:
            if abs(pipe_section.diameterNew - pipe_section.diameterRead) <= 0.0001 :
                print("Pipe No. :  " + str(pipe_section.elementId) + " did not need to be adjusted.") 
            else:
                changeCount += 1
                if inputData.geometry == True:
                    # print("I made it this far!!")
                    parameters = doc.GetElement(pipe_section.elementId).Parameters
                
                    for parameter in parameters:
                        if parameter.Definition.Name == "Diameter":
                            parameter.Set(float(pipe_section.diameterNew))
                        else:
                            continue
                print("Pipe No. : " + str(pipe_section.elementId) + \
                        " \n\t Was at : " + str(pipe_section.diameterRead * 12) + \
                        " \n\t Changed to : " + str(pipe_section.diameterNew * 12))
        else:
            continue
    t.Commit()

    print("Changed Size for " + str(changeCount) + " Elements!")
    if inputData.closeAfter:
        __window__.Close()

main()