
import asyncio
import pyvisa
import time
import pandas as pd
import os 

#####################################################################################################
#Keithley 236 Communication Set-up
#Configuration

address = 'GPIB0::16::INSTR'



df = pd.DataFrame(columns = ['Voltage ,Current'])
dataset_dir = "C:/Users/MYLab_Vostro/Documents/Smaract Probe station/Smaract-Labview/results"

def initialize_keithley236(address):
    """
    Define the visa address for Keithley 236 and initialize measurement parameters.
    """
    rm = pyvisa.ResourceManager()
    keithley = rm.open_resource(address)
    
    keithley.write('F0,0X')           # Force V measure I
    keithley.write('L0.01,0X')       # compliance current of 10mA on the 10mA range
    #keithley.write('L100E-3,9X') # compliance current of 100mA on the 100mA range
    keithley.write('H0X')             # Immediate trigger 
    keithley.write('G5,2,0X')       # Source and measure 
    return keithley


def measure_currentvoltage_keithley236():
    sweepresults = []
    sweepvoltage = -1
    sweeploopcount = 21
    for i in range(sweeploopcount):
        keithley.write('B' +str(sweepvoltage) +',0,0X')

        keithley.write('N1X')
        sweepvoltage = sweepvoltage + 0.1
        time.sleep(1)
        sweepresults.append(keithley.read())
        time.sleep(1)
        
        df.loc[len(df)] = sweepresults[i]
    keithley.write('N0X')
    return df
    

def export_to_csv(df, measurecount):
    filename = f'1-{measurecount}.csv'
    filepath = os.path.join(dataset_dir, filename)
        
    df.to_csv(filepath)
    df.drop(df.index , inplace=True)
    return df
    

async def init_measurement_keithley(count):
    initialize_keithley236(address)
    try:
        df = measure_currentvoltage_keithley236()
        df = export_to_csv(df, count)  
    except Exception as err:
        print("Failed to start measurement: {}\n".format(err))
        
        
async def do_measurement_keithley(count):
    initialize_keithley236(address)
    try:
        df = measure_currentvoltage_keithley236()
        df = export_to_csv(df, count) 
    except Exception as err:
        print("Failed to start measurement: {}\n".format(err))
########################################################################################################
#define SmarProbe functions
# Configuration
start_position = []  # will be current position at start of script
relative_end_position = [510.0E-6, 510.0E-6, 0.0]  # relative to start, give extra margin if end position is to be included
end_position = []  # set when start_position determined, from start_position + relative_end_position
step_size = [10.0E-6, 10.0E-6]  # x and y step size
auto_touch_height = 0.0  # height at auto touch, set after first auto touch in move_to_start_position
safe_movement_height = 25.0E-6  # height to move x and y in without risk of touching the surface, height relative (above) to auto touch height
approach_start_height = 20.0E-6  # move to this height faster then start auto touch, relative to auto touch height
transfer_velocity = 50.0E-6  # velocity for moving from one measurement point to the next in save height, m/s
approach_start_height_velocity = 5.0E-4  # velocity for moving to the approach_start_height, m/s
retract_scanning_velocity = 0.00005  # velocity for retracting from auto touch position to the upper limit of the scan range (equivalent to 0.5 scan range/s)
retract_velocity = 5.0E-6  # retract velocity after reaching maximum scan range, for closed loop movement
offset_height = 25.0E-6 #offset after autotouch command is finished  
offset_velocity = 5.0E-6
 
def prerequisites_check():
    """
    Get confirmation about the prerequisites from the user.
    :return: False if one not confirmed
    """
    prerequisites_message_list = \
        [
            "Are the configuration variables up to date?",
            "Are all axes of the used tower calibrated?",
            "Is the tower at the position for the first auto touch?",
            "Is nothing obstructing the scan area of the tower?",
            "Is the auto touch initialized?",
            "Is a custom electrical measurement set up in the GUI? [Optional]"
        ]
    for message in prerequisites_message_list:
        print(message + "\n")
        if not smarProbe.yesNoDialog(message, message) and not ("[Optional]" in message):
            print("Prerequisites not confirmed. Aborting!")
            return False
    return True
 
 
async def get_current_position(slot_index):
    """
    Returns the global position of the slot as a list of [x, y, z] in m.
    :param slot_index: Index of the slot
    :return: List of position [x, y, z] in m
    :pre
    """
    position = await smarProbe.getPosition(slot_index)
    print("Current position x, y, z: ({}, {}, {})\n".format(position[0], position[1], position[2]))
    return position
 
 
async def move_to_approach_start_height(slot_index):
    """
    Moves the slot at the current position to approach_start_height.
    :param slot_index: Index of the slot to be moved
    :return: No return
    :pre auto_touch_height needs to be determined by an auto touch or set appropriately
    """
    position = await get_current_position(slot_index)
    print("Moving to start height for auto touch\n")
    futures = smarProbe.move(slot_index,
                             [position[0], position[1], auto_touch_height + approach_start_height],
                             approach_start_height_velocity)
    await asyncio.wait(futures)
 

async def offset_autotouch_height(slot_index):
    """
    Moves the slot at the current position to approach_start_height.
    :param slot_index: Index of the slot to be moved
    :return: No return
    :pre auto_touch_height needs to be determined by an auto touch or set appropriately
    """
    position = await get_current_position(slot_index)
    print("Moving to offset height for auto touch\n")
    await smarProbe.setNoSlip(slot_index, False)
    futures = smarProbe.move(slot_index,
                             [position[0], position[1], auto_touch_height - offset_height],
                             offset_velocity)
    await asyncio.wait(futures)
  

async def do_auto_touch(slot_index):
    """
    Moves at the current position to the approach_start_height and then performs a save approach to the surface.
    Updates the auto_touch_height
    :param slot_index: Index of the slot to do an auto touch for
    :return: No return
    :pre auto_touch_height needs to be determined by a smarProbe.autoApproach or set appropriately
    """
    await move_to_approach_start_height(slot_index)
    await smarProbe.autoApproach(slot_index, auto_touch_callback)
    position = await get_current_position(slot_index)
    global auto_touch_height
    auto_touch_height = position[2]
    

async def do_auto_touch_offset(slot_index):
    """
    Moves at the current position to the approach_start_height and then performs a save approach to the surface.
    Updates the auto_touch_height
    :param slot_index: Index of the slot to do an auto touch for
    :return: No return
    :pre auto_touch_height needs to be determined by a smarProbe.autoApproach or set appropriately
    """
    await move_to_approach_start_height(slot_index)
    await smarProbe.autoApproach(slot_index, auto_touch_callback)
    position = await get_current_position(slot_index)
    global auto_touch_height
    auto_touch_height = position[2]
    await offset_autotouch_height(slot_index)
    
          
async def safe_retract(slot_index):
    """
    Moves up to maximum scan range.
    Sets NoSlip to false for the slot.
    Use to safely disengage from an auto touch position.
    :param slot_index: Index of the slot to retract
    :return: No return
    """
    await smarProbe.setNoSlip(slot_index, False)
    await smarProbe.scanMove(slot_index, 2, 100.0, retract_scanning_velocity, False)  # Move up to maximum scan range
     
 
async def move_to_save_travel_height(slot_index):
    """
    Safely retract from surface then move to safe_movement_height.
    :param slot_index: Index of slot to be moved to save height
    :return: No return
    """
    position = await get_current_position(slot_index)
    # retract in scan mode to max scan range
    print("Save retract\n")
    await safe_retract(slot_index)
    print("Retracted\n")
    # move to travel height
    print("Move to travel height\n")
    futures = smarProbe.move(slot_index,
                             [position[0], position[1], position[2] + safe_movement_height],
                             retract_velocity)
    await asyncio.wait(futures)
    print("At height\n")
 
 
async def move_to_next_position(slot_index):
    """
    From the current position moves the slot by step_size in x direction if <= end_position
    otherwise tries step_size in y direction at start_position of x.
    Expects end_position > start_position individually in x and y direction.
    :param slot_index: Index of slot to be moved
    :return: True if moved to position, False if step would result in position greater than end_position
    """
    await move_to_save_travel_height(slot_index)
    position = await get_current_position(slot_index)
    next_x = position[0] + step_size[0]
    if next_x <= end_position[0]:
        next_position = [next_x, position[1], position[2]]
        print("Target position x, y, z: ({}, {}, {})\n".format(next_position[0],
                                                               next_position[1],
                                                               next_position[2]))
        futures = smarProbe.move(slot_index, next_position, transfer_velocity)
        await asyncio.wait(futures)
        return True
    else:
        next_x = start_position[0]
        next_y = position[1] + step_size[1]
        if next_y <= end_position[1]:
            next_position = [next_x, next_y, position[2]]
            print("Target position x, y, z: ({}, {}, {})\n".format(next_position[0],
                                                                   next_position[1],
                                                                   next_position[2]))
            futures = smarProbe.move(slot_index, next_position, transfer_velocity)
            await asyncio.wait(futures)
            return True
        else:
            return False
 
 
async def move_to_start_position(slot_index):
    """
    Moves the slot to the start_position and performs an auto touch.
    Then retracts to save_travel_height above the auto touch height.
    Sets the auto touch height.
    :param slot_index: Index of slot to be moved
    :return: No return
    """
    futures = smarProbe.move(slot_index, start_position, transfer_velocity)
    await asyncio.wait(futures)
    await smarProbe.autoApproach(slot_index)
    position = await get_current_position(slot_index)
    global auto_touch_height
    auto_touch_height = position[2]
    await move_to_save_travel_height(slot_index)
 
 
async def setup_movement_range(slot_index):
    """
    Setup the movement range in which the measurement points lie from the current position and the relative_end_position
    """
    current_position = await get_current_position(slot_index)
    start_position.clear()
    end_position.clear()
    start_position.append(current_position[0])
    start_position.append(current_position[1])
    start_position.append(current_position[2])
    end_position.append(start_position[0] + relative_end_position[0])
    end_position.append(start_position[1] + relative_end_position[1])
    end_position.append(start_position[2] + relative_end_position[2])
 
 
async def do_measurement(slot_index):
    """
    Performs an electrical measurement with the Keithley Parameter Analyser.
    Data is returned to the callback function measurement_callback.
    The measurement needs to be configured before hand in the GUI as custom electrical measurement.
    :param slot_index: Slot to perform the measurement with the connected SMU
    :return: Via callback function measurement_callback
    """
    try:
        await smarProbe.electricalMeasurement({slot_index: measurement_callback})
    except Exception as err:
        print("Failed to start measurement: {}\n".format(err))
        time.sleep(20)
 
 
def measurement_callback(step_name, voltage, current):
    """
    Callback function to handle the measurement data from do_measurement.
    :param step_name: Name of the step, or empty
    :param voltage: Current voltage value
    :param current: Current current value
    :return: No return
    """
    print("Step: {}, voltage: {}, current: {}\n".format(step_name, voltage, current))
    # save data to object, or file to process later or process now
    # get current position for complete data set ...
 
 
def auto_touch_callback(data_point):
    """
    Callback function to receive z position data during auto touch movement.
    :param data_point: Tuple of (time, z position); time relative to auto touch start
    :return: No return
    """
    time, z_position = data_point
    print("Current z position: time: {} - position: {}\n".format(time, z_position))
    # save data to object, or file to process later or process now
 
 
async def run(slot_index):
    """
    Moves the slot from start_position to end_position in step_size steps.
    At each position an auto touch and then an electrical measurement is performed.
    :param slot_index: Index of slot to be moved
    :return: No return
    :pre see prerequisites_reminder
    """
    if not prerequisites_check():
        return
 
    await setup_movement_range(slot_index)
    await move_to_start_position(slot_index)
    # Perform a measurement at the start position
    await do_auto_touch(slot_index)
    # await move_to_approach_start_height(slot_index)  # save replacement for auto touch
    await do_measurement(slot_index)
 
    # Move in a grid, performing measurements at each point
    while await move_to_next_position(slot_index):
        await do_auto_touch(slot_index)
        # await move_to_approach_start_height(slot_index)  # save replacement for auto touch
        await do_measurement(slot_index)
    print("Raster movement finished")


async def run_keithley(slot_index):
    count = 2
    if not prerequisites_check():
        return
        
    await setup_movement_range(slot_index)
    await move_to_start_position(slot_index)
    # Perform a measurement at the start position
    await do_auto_touch_offset(slot_index)
    await init_measurement_keithley(1)  

    # Move in a grid, performing measurements at each point
    while await move_to_next_position(slot_index):
        await do_auto_touch_offset(slot_index)
        # await move_to_approach_start_height(slot_index)  # save replacement for auto touch
        await do_measurement_keithley(count)  
        count = count + 1

    print("Raster movement finished")
    # await move_to_approach_start_height(slot_index)  # save replacement for auto touch

keithley = initialize_keithley236(address)