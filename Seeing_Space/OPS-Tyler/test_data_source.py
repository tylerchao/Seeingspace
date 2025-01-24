import array
import time
from mqtt import mqtt
import subprocess

def states_array(count):
    array= []
    array.append("home")
    array.append("wait_for_connection")
    array.append("wait_for_data")
    array.append("move_to_target")
    array.append("clamping")
    array.append("move_to_calib_area")
    array.append("calibrating")
    array.append("move_to_tower_area")
    array.append("build_tower")
    array.append("move_to_home")    

    state = array[count]
    return state

def blocks_array_x():
    array = []  # Creating a 2D array with 4 rows and 4 columns
    array.append(234)
    array.append(145)
    array.append(229)
    array.append(456)
    return array
    
def blocks_array_y():
    array = []  # Creating a 2D array with 4 rows and 4 columns
    array.append(388)
    array.append(245)
    array.append(222)
    array.append(333)
    return array
    

def run(tool_pos_z, no_blocks, gripper):

    gripper_state = gripper

    program_state = states_array(count)
    print(program_state)
    
    tool_pos_x = 124     
    tool_pos_y = 389

    block_pos_x=blocks_array_x()[block_appear_time] 
    block_pos_y=blocks_array_y()[block_appear_time]
    block_xandy = (block_pos_x, block_pos_y) 
    block_pos_z = 100
    
    block_angle = 122
    
    # mqtt.publish(client, "replay", "here is replay ")
    # mqtt.publish(client, "record", "here is record ")
    
    mqtt.publish(client, "kuka/no_blocks", no_blocks)
    mqtt.publish(client, "kuka/gripper_state", gripper_state)
    mqtt.publish(client, "kuka/program_state", program_state)
    
    mqtt.publish(client, "kuka/tool/coord_x", tool_pos_x)
    mqtt.publish(client, "kuka/tool/coord_y", tool_pos_y)
    mqtt.publish(client, "kuka/tool/coord_z", tool_pos_z)
    
    # mqtt.publish(client, "kuka/block/coord_xandy", block_xandy)

    mqtt.publish(client, "kuka/block/coord_x", block_pos_x)
    mqtt.publish(client, "kuka/block/coord_y", block_pos_y)
    mqtt.publish(client, "kuka/block/coord_z", block_pos_z)

    mqtt.publish(client, "kuka/block/angle", block_angle)

    mqtt.publish(client, "kuka/level", level)

global level 
if __name__ == '__main__':
    count=0
    level=0
    no_blocks = False
    block_appear_time = 0 
    client = mqtt.connect_mqtt()
    client.loop_start()
    tool_pos_z=689
    gripper = "open"
    while True:

        if tool_pos_z < 100:
            tool_pos_z = 689

        tool_pos_z -= 100
       
        count += 1
        if count > 9:
            count = 0

        if count % 6 == 0:
            level += 1
            if level > 18:
                level = 0
                no_blocks = False
            elif level >2:
                no_blocks = True

        #if count % 6 == 0:
        block_appear_time +=1
        if block_appear_time > 3:
            block_appear_time = 0


        if count % 3 == 0:
            gripper = "open"
        else :
            gripper= "close"


        run(tool_pos_z,no_blocks,gripper)

        time.sleep(1.0) 

        # if(tool_pos_z < 100):
        #     tool_pos_z =689

        # tool_pos_z =tool_pos_z - 100
        # run(tool_pos_z)
       
        # count = count +1
        # time.sleep(1.0)
        # if(count>9):
        #     count = 0

        # time.sleep(3.0)
        # level = level + 1
        # if (level >18):
        #     level=0

        



        