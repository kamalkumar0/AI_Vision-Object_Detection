from flask import Flask, render_template, Response, jsonify, request
from ultralytics import YOLO
import cv2

def find_camera_index():
    for index in [1, 2, 0]:
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                return index
    return 1

app = Flask(__name__)
model = YOLO("yolo11n.pt") 

# YOLO model se saari 80 classes nikal lenge (0: person, 1: bicycle, etc.)
CLASS_NAMES = model.names 

camera = None
is_running = False
latest_objects = []
current_filter_class = None # Agar None hai, toh sab kuch dikhayega

def generate_frames():
    global camera, is_running, latest_objects, current_filter_class
    
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(find_camera_index(), cv2.CAP_DSHOW)
        
    while is_running:
        success, frame = camera.read()
        if not success:
            break
            
        # Filter logic: Agar koi specific object select kiya hai, toh prediction me pass kardo
        predict_kwargs = {"source": frame, "conf": 0.5, "verbose": False}
        if current_filter_class is not None:
            predict_kwargs["classes"] = [current_filter_class]
            
        results = model.predict(**predict_kwargs)
        
        current_objects = []
        for r in results:
            for c in r.boxes.cls:
                current_objects.append(model.names[int(c)])
        
        latest_objects = list(set(current_objects)) 
        annotated_frame = results[0].plot() 
        
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_camera')
def start_camera():
    global is_running
    is_running = True
    return jsonify({"status": "Camera Started"})

@app.route('/stop_camera')
def stop_camera():
    global is_running, camera, latest_objects
    is_running = False
    latest_objects = []
    if camera is not None:
        camera.release()
        camera = None
    return jsonify({"status": "Camera Stopped"})

@app.route('/video_feed')
def video_feed():
    if not is_running:
        return ""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_objects')
def get_objects():
    global latest_objects
    return jsonify({"objects": latest_objects})

# --- Naye Endpoints Filter Dropdown ke liye ---

@app.route('/get_classes')
def get_classes():
    return jsonify(CLASS_NAMES)

@app.route('/set_filter', methods=['POST'])
def set_filter():
    global current_filter_class
    data = request.json
    class_id = data.get('class_id')
    
    if class_id == 'all':
        current_filter_class = None
    else:
        current_filter_class = int(class_id)
        
    return jsonify({"status": "Filter updated"})

if __name__ == '__main__':
    app.run(debug=True)