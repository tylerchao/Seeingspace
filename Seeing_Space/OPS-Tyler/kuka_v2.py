import time
from mqtt import mqtt
from py_openshowvar import openshowvar
import paho.mqtt.client as paho 
  
class RemoteControlKUKA:

    def __init__(self, address="192.168.1.15", port=7000, debug=False):
        self.debug = debug
        self._client = openshowvar(address, port)
        if (not self._client.can_connect):
            raise RuntimeError("Unable to connect.")
            
    def __del__(self):
        self._client.close()

    def _read(self, identifier, debug=False):
        return self._client.read(identifier, debug=debug)
        
    def _write(self, identifier, value, debug=False):
        return self._client.write(identifier, value, debug=self.debug or debug)


    def get_no_blocks(self):
        no_blocks = self._read("CHECKING_WARNING")
        if(no_blocks == b'TRUE'):
            return True
        else:
            return False

    def get_gripper_states(self):
        gripper_close = self._read("$OUT[1]")
        gripper_open = self._read("$OUT[2]")
        if(gripper_close == b'TRUE'and gripper_open == b'FALSE'):
                return "close"     
        elif(gripper_open == b'TRUE'and gripper_close== b'FALSE'):
                return "open"


    def get_program_state(self):
        if(self._read("ROBOT_STATES[10]") == b'TRUE'):
            return "move_to_home"
        elif(self._read("ROBOT_STATES[9]") == b'TRUE'):
            return "build_tower"
        elif(self._read("ROBOT_STATES[8]")== b'TRUE'):
            return "move_to_tower_area"
        elif(self._read("ROBOT_STATES[7]")== b'TRUE'):
            return "calibrating"
        elif(self._read("ROBOT_STATES[6]") == b'TRUE'):
            return "move_to_calib_area" 
        elif(self._read("ROBOT_STATES[5]") == b'TRUE'):
            return "clamping"
        elif(self._read("ROBOT_STATES[4]")== b'TRUE'):
            return  "move_to_target"
        elif(self._read("ROBOT_STATES[3]")== b'TRUE'):
            return "wait_for_data"
        elif(self._read("ROBOT_STATES[2]")== b'TRUE'):
            return "wait_for_connection"
        else:
            return "home"

    def get_block_x(self):
        block_position = self.transform_coordinate(self._read("BlockPos"))
        return block_position['X']

    def get_block_y(self):
        block_position = self.transform_coordinate(self._read("BlockPos"))
        return block_position['Y']

    def get_block_x_y(self):
        block_position = self.transform_coordinate(self._read("BlockPos"))
        return (block_position['X'], block_position['Y'])

    def get_block_z(self):
        block_position = self.transform_coordinate(self._read("BlockPos"))
        return block_position['Z']

    def get_block_angle(self):
        block_angle = self.transform_coordinate(self._read("BlockPos"))
        return block_angle['A']

    def get_pos_x(self):
        pos_x = self._read("$POS_ACT")
        tool_position = self.transform_coordinate(pos_x)
        return tool_position['X']     
   
    def get_pos_y(self):
        tool_position = self.transform_coordinate(self._read("$POS_ACT"))
        return tool_position['Y']
   
    def get_pos_z(self):
        tool_position = self.transform_coordinate(self._read("$POS_ACT"))
        return tool_position['Z']

    def get_level(self):
        return self._read("JENGA_LEVEL").decode('ASCII')
    
    def is_idle(self):
        return b'0' == self._read("COM_ACTION")
        
    def _set_e6pos(self, e6pos):
        self._write("COM_E6POS",e6pos) 
        
    def _set_action(self, s_action):
        if (s_action == "PTP_E6POS"):
            a = 11
        elif (s_action == "LIN_E6POS"):
            a = 12
        else:
            raise NotImplementedError("Unknown action string.")
        self._write("COM_ACTION", str(a))

    def _wait(self, wait=True):
        while (wait and not rck.is_idle()):
            time.sleep(0.1)

    def move_lin_e6pos(self, e6pos, block=True):
        self._set_e6pos(e6pos)
        self._set_action("LIN_E6POS")
        print("here")
        self._wait(block)

    def move_ptp_e6pos(self, e6pos, block=True):
        self._set_e6pos(e6pos)
        self._set_action("PTP_E6POS")
        self._wait(block)

    def transform_coordinate(self,identifier):
        try:
            identifier_str = identifier.decode('ascii')
            identifier_parts =identifier_str.strip().strip('{}').split(':')[1].split(',')
            identifier_pairs = [item.strip().split(' ') for item in identifier_parts]
            identifier_pairs = [(k,float(v)) for k,v in identifier_pairs]
            identifier_position = dict(identifier_pairs)
            return identifier_position
        except:
            identifier_position = {'X': '0', 'Y': '0', 'Z': '0','A':'0'}
            return identifier_position


if __name__ == '__main__':
    rck = RemoteControlKUKA()
    client = mqtt.connect_mqtt()
    client.loop_start()
    temp_state = "none"
    temp_no_blocks = True
    temp_gripper_state = True
    temp_block_pos_x = 0
    temp_block_pos_y = 0
    
    temp_level = 0
    temp_tool_pos_x = 0
    temp_tool_pos_y = 0
    temp_tool_pos_z = 0
    time_interval_gripper = 95
    
    while True:

        currentime_gripper = time.time()
        # print(currentime)

        # flag with blocks on the board 
        no_blocks = rck.get_no_blocks()
        if temp_no_blocks != no_blocks:
            mqtt.publish(client, "kuka/no_blocks", no_blocks)
        temp_no_blocks = no_blocks

      

        #if temp_gripper_state != gripper_state:
            
        #temp_gripper_state = gripper_state

        # block coordinate amd angle 
        block_pos_x = rck.get_block_x()
        block_pos_y = rck.get_block_y()
        block_xandy = rck.get_block_x_y()
        block_pos_z = rck.get_block_z()
        block_angle = rck.get_block_angle()

        

        if temp_block_pos_x !=block_pos_x  and  temp_block_pos_y != block_pos_y:
            
            mqtt.publish(client, "kuka/block/coord_x", block_pos_x)
            mqtt.publish(client, "kuka/block/coord_y", block_pos_y)

            mqtt.publish(client, "kuka/block/coord_xandy", block_xandy)

            mqtt.publish(client, "kuka/block/coord_z", block_pos_z)
            mqtt.publish(client, "kuka/block/angle", block_angle)
        temp_block_pos_x = block_pos_x
        temp_block_pos_y = block_pos_y


        # flag of which building level is 
        level = rck.get_level()
        if temp_level != level:
            mqtt.publish(client, "kuka/level", level)
        temp_level =  level

        # which states is now 
        program_state = rck.get_program_state()
        
        if temp_state != program_state:
            mqtt.publish(client, "kuka/program_state", program_state)
        temp_state = program_state

          
         #   tool position
        tool_pos_x = rck.get_pos_x()
        tool_pos_y = rck.get_pos_y()
        tool_pos_z = rck.get_pos_z()

       
        # print((time.time() - currentime_gripper)*1000)
        
        # gripper state 
        gripper_state = rck.get_gripper_states()

        if (time.time() - currentime_gripper)*1000 >= time_interval_gripper:

            mqtt.publish(client, "kuka/gripper_state", gripper_state)
               
            mqtt.publish(client, "kuka/tool/coord_x", tool_pos_x)
            mqtt.publish(client, "kuka/tool/coord_y", tool_pos_y)
            mqtt.publish(client, "kuka/tool/coord_z", tool_pos_z)   

            currentime_gripper = time.time()*1000

        #if time.time()*100 - currentime_tool >= time_interval_tool:
         

          #  currentime_tool = time.time()*100

        # print(currentime)
       
        
        # if abs(temp_tool_pos_x-int(tool_pos_x)) > 1.0:
        #     mqtt.publish(client, "kuka/tool/coord_x", tool_pos_x)
        # if abs(temp_tool_pos_y-int(tool_pos_y)) > 1: 
        #     mqtt.publish(client, "kuka/tool/coord_y", tool_pos_y)
        # if abs(temp_tool_pos_z-int(tool_pos_z)) > 1:
        #     mqtt.publish(client, "kuka/tool/coord_z", tool_pos_z)

        # temp_tool_pos_x = int(tool_pos_x)
        # temp_tool_pos_y = int(tool_pos_y)
        # temp_tool_pos_z = int(tool_pos_z)

     
        
        
       
        