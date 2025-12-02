import cv2 as cv

video = cv.VideoCapture(1)
while True:
    ret, frame = video.read()
    cv.imshow("Frame", frame)
    if cv.waitKey(1) & 0xFF == ord("q"):
        break

video.release()
cv.destroyAllWindows()