from multiprocessing import Process
from datetime import datetime
from time import sleep
from config import CONFIG
import numpy as np
import os

from jetson_inference import detectNet
from jetson_utils import videoSource, videoOutput
import cv2
import threading 
import time
from random import randint
import keyboard
from pydub import AudioSegment
from pydub.playback import play
import psutil

from os.path import exists
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import smtplib
import ssl


class Mail:
    def __init__(self):
        self.receiver_mail = CONFIG["email"]["receiver_email"]
        self.smtp_server_domain_name = CONFIG["email"]["smtp_server_domain_name"]
        self.sender_mail = CONFIG["email"]["sender_mail"]
        self.password = CONFIG["email"]["password"]
        self.port = CONFIG["email"]["port"]
    def send(self):
        filename = "dogs_detected.csv"
        msg = MIMEMultipart()
        msg["From"] = self.sender_mail
        msg["To"] = self.receiver_mail
        # msg["Subject"] = "Dog report"

        with open("dogs_detected.csv", "r") as file:
            content = file.read()

        msg.attach(MIMEText(content, "plain"))

        # attachment = MIMEBase("application", "octet-stream")
        # attachment.set_payload(open(filename, "rb").read())
        # encoders.encode_base64(attachment)
        # attachment.add_header("Content-Disposition", "attachment", filename=filename)
        # msg.attach(attachment)

        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(self.smtp_server_domain_name, self.port, context=context)

        try:
            server.login(self.sender_mail, self.password)
            server.sendmail(self.sender_mail, self.receiver_mail, msg.as_string())
        except smtplib.SMTPException as e:
            print("Failed to send email. Error:", e)

        server.close()

class VideoWindow():
    def __init__(self):
        self.BgVids = CONFIG["video_settings"]["background_video_paths"]
        self.DogVids = CONFIG["video_settings"]["dog_video_paths"]
        self.BgVidsLen = len(self.BgVids)
        self.DogVidsLen = len(self.DogVids)
        self.audio = AudioSegment.from_file("audios/detected.wav", format = "wav")      
        
    def run_dog(self):
        video = self._get_random_dog()        
        #cap = cv2.VideoCapture('filesrc location=videos/dog_videos/detected.mp4 ! qtdemux ! queue ! h264parse ! omxh264dec ! nvvidconv ! video/x-raw,format=BGRx,width=720,height=1280 ! queue ! videoconvert ! queue ! video/x-raw, format=BGR ! appsink', cv2.CAP_GSTREAMER)
        cap = cv2.VideoCapture('videos/dog_videos/detected.mp4')
        if cap.isOpened() == False:
            print("Error opening video file")
            
        
        cv2.namedWindow('Frame', cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty('Frame', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        suspended = 5 #display the first five frames to avoid gaps betixt videos
        thr = threading.Thread(target = self.play_sound)
        thr.start()
        while(cap.isOpened()):
            ret, frame = cap.read()                
            if ret == True:
                cv2.imshow('Frame', frame)
            else:
                break
            if cv2.waitKey(40) & 0xFF == ord('q'):
                break
            suspended = suspended - 1
            if not suspended:
                ps_process.suspend()
            
        ps_process.resume()
        thr.join()
        cap.release()
        cv2.destroyAllWindows()

    def run_background(self):
        cv2.namedWindow('Frame', cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty('Frame', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)  
        while True:
            
            #cap = cv2.VideoCapture('filesrc location=videos/background_videos/bg_vid.mp4 ! qtdemux ! queue ! h264parse ! omxh264dec ! nvvidconv ! video/x-raw,format=BGRx,width=720,height=1280 ! queue ! videoconvert ! queue ! video/x-raw, format=BGR ! appsink', cv2.CAP_GSTREAMER)
            cap = cv2.VideoCapture('videos/background_videos/bg_vid.mp4')
            if cap.isOpened() == False:
                print("Error opening video file")
       
                  
            while(cap.isOpened()):
                ret, frame = cap.read()          
            
                if ret == True:
                    cv2.imshow('Frame', frame)
                else:
                    break
                if cv2.waitKey(40) & 0xFF == ord('q'):
                    break

            cap.release()

    def _get_random_dog(self):
        return self.DogVids[randint(0, self.DogVidsLen - 1)]

    def play_sound(self):
        print("play_sonud() called")
        play(self.audio)
        print("audio finished")


class DropFrameException(Exception):
    def __init__(self):
        return

class Classifier():
    def __init__(self):
        self.show_preview = CONFIG["camera_settings"]["show_preview"]
        self.camera_idx = CONFIG["camera_settings"]["camera_idx"]
        self.net = detectNet("coco-dog", threshold = 0.9)
        self.display = videoOutput("display://0")

    def classify_from_live_stream(self):
        string = "error"
        
        if self.camera_idx:
            string = "/dev/video1"
        else:
            string = "csi://0"
        self.camera = videoSource(string)
        if os.path.exists("/.dockerenv"):
            print("Unable to run live stream in docker")
            exit(1)
        
        while self.display.IsStreaming():
            img = self.camera.Capture()
            if img is None:
                continue
            detections = self.net.Detect(img)
            if len(detections) > 0:                
                print("DOG FOUND")
                VideoWindow().run_dog()
                now_datetime = datetime.now().strftime("%Y-%m-%d,%H:%M:%S")
                with open("dogs_detected.csv", "a") as file:
                    file.write(now_datetime + "\n")

            if self.show_preview:
                self.display.Render(img)


def mail():
    #sends an email with the csv file every x minutes
    x = 15
    m = Mail()
    while True:
        m.send()
        time.sleep(x*60)
    
process = Process(target = VideoWindow().run_background)
process.start()
ps_process = psutil.Process(pid=process.pid)
def main():    
    c = Classifier()
    Process(target=mail).start()
    c.classify_from_live_stream()
    exit(0)    

if __name__ == '__main__':
    main()
