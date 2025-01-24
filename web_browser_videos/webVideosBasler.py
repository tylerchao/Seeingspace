from flask import Flask,render_template,Response
from pypylon import pylon
import cv2
import time

camera=None

def setup():
   print("Setup invoked")
   global camera
   if camera != None:
       print("already initialized")
       return
   
   # Connect to the first available camera
   camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

   # Set camera parameters
   camera.Open()
 
   camera.OffsetX.SetValue(0)
   camera.OffsetY.SetValue(0)
   camera.Width.SetValue(1600)
   camera.Height.SetValue(1200)
   camera.ReverseX.SetValue(True)
   camera.ReverseY.SetValue(True)
   camera.PixelFormat.SetValue("RGB8")  # Set pixel format to RGB8

# Start the video capture
   camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

def generate_frames():

    # Create a video writer object to save the video
    # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    # video_fps = 25
    # video_count = 0
    # out = cv2.VideoWriter(f'output_{video_count}.mp4v', fourcc, video_fps, (1600, 1200))
    # frame_count = 0

    while camera.IsGrabbing():
        ## read the camera frame 
        # Wait for a new frame
        grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if not grabResult.GrabSucceeded():
            break
        else:
            # Convert the image to a numpy array and display it
            img = cv2.cvtColor(grabResult.Array, cv2.COLOR_RGB2BGR)
            #img = grabResult.Array
#           cv2.imshow("Live Feed", img)
            # Write the frame to the video file
            # out.write(img)
            # frame_count += 1
            # if (frame_count > video_fps*10):
            #    out.release()
            #    out = None
            #    frame_count = 0
            #    video_count += 1
            #    out = cv2.VideoWriter(f'output_{video_count}.mp4v', fourcc, video_fps, (1600, 1200))

            ret, buffer = cv2.imencode('.jpeg', img)
            frame = buffer.tobytes()
            #get pieces of iomage 
            # ms = time.time_ns() // 1_000_000
            # with open(f'frame_{ms}.jpg', 'wb') as f:
            #     f.write(frame)
            
            # Release the current frame
            grabResult.Release()
        
            yield(b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n'+frame+b'\r\n')

app=Flask(__name__)

# add the directory containing your templates to the app's search path
app.template_folder =  '/Users/Cognex/Desktop/web_browser_videos/'

# alternatively, you can use the add_template_folder method
#app.add_template_folder('/path/to/templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    try:
      setup()
      app.run(host='0.0.0.0',port=5001,debug=True, use_reloader=False)
    finally:
       print("closing all ressources")
       # Release resources and close windows
       camera.StopGrabbing()
       # out.release()
       cv2.destroyAllWindows()
       camera.Close()
