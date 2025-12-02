import cv2 as cv

def list_ports():
    """
    Test the ports and returns a tuple with the available ports and the ones that are working.
    """
    is_working = True
    dev_port = 0
    working_ports = []
    available_ports = []
    
    print("Scanning camera indices 0-20...")
    
    while dev_port < 20:
        # Try with CAP_DSHOW which is often better for Windows USB cameras
        camera = cv.VideoCapture(dev_port)
            
        if camera.isOpened():
            is_reading, img = camera.read()
            w = camera.get(3)
            h = camera.get(4)
            if is_reading:
                print(f"Port {dev_port} is working and reads images ({w}x{h})")
                working_ports.append(dev_port)
            else:
                print(f"Port {dev_port} is present but cannot read images ({w}x{h})")
                available_ports.append(dev_port)
            camera.release()
        dev_port += 1
        
    return available_ports, working_ports

if __name__ == "__main__":
    available, working = list_ports()
    print(f"\nSummary:")
    print(f"Working indices: {working}")
    print(f"Available but not reading: {available}")
