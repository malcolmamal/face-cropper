# MalcolmRey's Face Cropper

## 0. Prerequisites 

Python, most likely any 3.x would do, but I'm currently running it on 3.10.8

## 1. Installation 
### for Windows
```bash
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```
### for Linux
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Running
```bash
python main.py --resolution=RESOLUTION --source-path=SOURCE_PATH --target-path=TARGET_PATH
```

* `RESOLUTION` is the cropping resolution (usually one of the following: `512`, `768`, `1024`)
at the moment only square resolution is supported, default is `512`
* `SOURCE_PATH` is the path where the original images are fetched from, you should have subfolder for each person for 
  example:
    ```bash
    SOURCE_PATH
      ritaora
      billieeilish
      henrycavill
      someoneelse
  ```
  there should be at least one subfolder for the script to do something, but if there are more, all will be cropped
* `TARGET_PATH` is the path where the outputs will be saved
  ```bash
  TARGET_PATH
    cropped
      ritaora
      billieeilish
      henrycavill
      someoneelse
  ```
  You only need to make sure that the `TARGET_PATH` exists, other subfolders will be created automatically


## Troubleshooting
* If the script is running slow, check if the `DLIB` library is using `CUDA`:
  ```bash
  python main.py --check-dlib
  ```
  If the result is false then you have to compile the DLIB library for CUDA: https://www.linkedin.com/pulse/installing-dlib-cuda-support-windows-10-chitransh-mundra
* If you get some errors -> please report them to me, I will try to do my best to help with them / improve the code
* Tested with `jpg`, `png` and `webp` formats but most likely others should work too
* For best experience, try using images with only one person in the photo, there is however some code to recognize which person is our target but this code is WIP still
* Currently only square resolutions are available (this is why you only provide one value)
* If you want to crop to higher res (768 or 1024) then smaller images will get upscaled
* There is no up-scaling for 512 images though
* Technically you can crop to any resolution, but I have not tested other resolutions besides the 3 supported ones
* If something is wrong with an image and I recognize it (wrong format, too big, etc.) I will skip it and proceed to the next, you can check the output for `skipped files` if you are interested in the files that were problematic

## External links

### Dlib Installation
* https://stackoverflow.com/questions/51943050/dlib-not-using-cuda
* https://www.geeksforgeeks.org/how-to-install-dlib-library-for-python-in-windows-10/
* https://github.com/ageitgey/face_recognition/issues/1143 (check comment about cpu)
* https://www.linkedin.com/pulse/installing-dlib-cuda-support-windows-10-chitransh-mundra
* https://discourse.cmake.org/t/cmake-issues-in-creation-of-dlib-for-gpu-in-windows/6260

### Face Recognition
* https://pypi.org/project/face-recognition/

### MalcolmRey's links
* CIVITAI profile: http://civitai.com/user/malcolmrey
* BuyMeACoffee: https://www.buymeacoffee.com/malcolmrey