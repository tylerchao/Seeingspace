from flask import Flask,render_template,Response
import cv2
import time
import os
import datetime

import paho.mqtt.client as mqtt

app=Flask(__name__)
camera = cv2.VideoCapture(0)

save_path = 'C:/Users/Cognex/Desktop/Tyler-SeeingSpace_v10/web_browser_videos_test/img/'

# MQTT broker configuration
broker = 'localhost'
port = 1883
topic = 'mqtt-replay-record/record'
recording = False
frame_gap= 0

# MQTT event callbacks
def on_connect(client, userdata, flags, rc):
    print('Connected to MQTT broker')
    client.subscribe(topic)

def on_message(client, userdata, msg):
    print(msg.payload.decode())
    print('Received MQTT message: ' + msg.payload.decode())
    global recording
    if msg.payload == b'start record':
        recording= True
    elif msg.payload == b'stop record':
        recording = False
   
# Initialize MQTT client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(broker, port, 60)
mqtt_client.loop_start()

def generate_frames():
    # Define the codec and create VideoWriter object
    # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    # out = cv2.VideoWriter('output.mp4v', fourcc, 20.0, (640, 480))

    current_time = time.time()

    #file_path = os.path.join(save_path, filename)

    # Create a video writer object to save the video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_fps = 25
    # video_count = 0
    out = cv2.VideoWriter(f'output.mp4v', fourcc, video_fps, (640, 480))
    frame_count = 0

    while(camera.isOpened()):
        ## read the camera frame 
        success,frame = camera.read()

        if not success:
            break
        else:
            # Write the frame to the video file
            # if recording :
            #     out.write(frame)

            #     if (frame_count > video_fps*5):
            #     # if time.time() - current_time >= frame_gap:
            #         out.release()
            #         out = None
            #         frame_count = 0
            #         # video_count += 1
            #         current_datetime = datetime.datetime.now()
            #         filename = current_datetime.strftime("%Y%m%d_%H%M%S")
            #         out = cv2.VideoWriter(f'{filename}.mp4v', fourcc, video_fps, (640, 480))
                    
            #         # current_time = time.time()
                
            #     frame_count += 1
            
            ret,buffer=cv2.imencode('.jpeg', frame)
            frame=buffer.tobytes()
            # out.release()
            if recording and time.time() - current_time >= frame_gap :
                #get pieces of image 
                current_datetime = datetime.datetime.now()
                filename = current_datetime.strftime("%Y%m%d_%H%M%S.jpg")

                file_path = os.path.join(save_path, filename)

                with open(file_path, 'wb') as f:
                    f.write(frame)

                current_time = time.time()
            
                # ms = time.time_ns() // 1_000_000
                # with open(f'frame_{}.jpg', 'wb') as f:
                #     f.write(frame)
               
            # Release the current frame
            yield(b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n'+frame+b'\r\n')
              
# add the directory containing your templates to the app's search path
app.template_folder = '/Users/tyler/Documents/web_browser_videos/'

# alternatively, you can use the add_template_folder method
#app.add_template_folder('/path/to/templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Example route to subscribe to MQTT topic
@app.route('/subscribe')
def subscribe():
    mqtt_client.subscribe(topic)
    return 'Subscribed to topic: ' + topic

if __name__ == "__main__":
    try :
        app.run(host='0.0.0.0',port=5000,debug=True)
    finally:
       print("closing all ressources")
       camera.release()
       out.release()
       cv2.destroyAllWindows()
      
