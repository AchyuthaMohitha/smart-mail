"""
face_lock.py - Face verification for logging in (PPT slide 10).

How it works:
  1. The lock screen opens your webcam in the browser and takes one picture.
  2. OpenCV reads the picture and checks that the face is bright enough (PPT
     slide 14: poor lighting was a real problem, so we warn instead of guessing).
  3. face_recognition finds the face and turns it into 128 numbers called an
     "encoding" (a face fingerprint).
  4. The encoding is compared with the owner's saved encoding. If the
     difference ("distance") is small enough, it is the same person.

Detecting A face is not enough - it must MATCH the registered owner.
If the face libraries are not installed, or the webcam doesn't work,
the owner can unlock with Google sign-in instead (see app.py).

Known limitation (be honest in the viva): a printed photo of the owner
might fool this system, because we don't check for "liveness".
"""

import base64

import numpy as np

import config

# The face libraries are optional. If they are missing, Face-Lock is turned off.
try:
    import cv2
    import face_recognition
    FACE_LIBRARIES_AVAILABLE = True
except ImportError:
    FACE_LIBRARIES_AVAILABLE = False

MATCH_TOLERANCE = 0.5   # smaller = stricter. face_recognition's default is 0.6
MIN_BRIGHTNESS = 50     # average pixel brightness (0 = black, 255 = white)
MAX_IMAGE_WIDTH = 800   # big photos are shrunk first so detection is fast


class FaceLockError(Exception):
    """A friendly message to show the user (too dark, no face, etc.)."""


def is_available():
    return FACE_LIBRARIES_AVAILABLE


def owner_face_registered():
    return config.FACE_DATA_PATH.exists()


def data_url_to_bytes(data_url):
    """The browser sends 'data:image/jpeg;base64,....'. Return the image bytes."""
    if not data_url or "," not in data_url:
        raise FaceLockError("No picture was received from the webcam.")
    try:
        return base64.b64decode(data_url.split(",", 1)[1])
    except Exception:
        raise FaceLockError("The picture from the webcam could not be read.")


def get_face_encoding(image_bytes):
    """
    Return the 128-number encoding of the ONE face in the picture.
    Raises FaceLockError if the picture is unreadable, too dark, or doesn't have exactly one face.
    """
    if not FACE_LIBRARIES_AVAILABLE:
        raise FaceLockError("Face-Lock is not installed on this computer. Use Google sign-in instead.")

    # OpenCV: decode the bytes into an image (OpenCV uses Blue-Green-Red colour order).
    image_bgr = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise FaceLockError("The picture could not be read.")

    height, width = image_bgr.shape[:2]
    if width > MAX_IMAGE_WIDTH:
        scale = MAX_IMAGE_WIDTH / width
        image_bgr = cv2.resize(image_bgr, (int(width * scale), int(height * scale)))

    too_dark = "The picture is too dark. Turn on a light or face a window and try again."
    grey = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)   # OpenCV: grey picture for brightness

    # face_recognition expects Red-Green-Blue order.
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(image_rgb)
    if len(face_locations) == 0:
        # No face: if the whole picture is dark, darkness is the most likely reason.
        if grey.mean() < MIN_BRIGHTNESS:
            raise FaceLockError(too_dark)
        raise FaceLockError("No face found. Look straight at the camera and try again.")
    if len(face_locations) > 1:
        raise FaceLockError("More than one face found. Only the owner should be in the picture.")

    # Brightness of the FACE itself (a dark room behind a well-lit face is fine).
    top, right, bottom, left = face_locations[0]
    if grey[top:bottom, left:right].mean() < MIN_BRIGHTNESS:
        raise FaceLockError(too_dark)

    return face_recognition.face_encodings(image_rgb, face_locations)[0]


def register_owner_face(image_bytes):
    """Save the owner's face encoding (only the 128 numbers, not the photo)."""
    encoding = get_face_encoding(image_bytes)
    config.create_folders()
    np.save(config.FACE_DATA_PATH, encoding)


def remove_owner_face():
    if owner_face_registered():
        config.FACE_DATA_PATH.unlink()


def verify_face(image_bytes):
    """
    Compare the face in the picture with the registered owner.
    Returns (is_match, distance). Raises FaceLockError for problems like "too dark".
    """
    if not owner_face_registered():
        raise FaceLockError("No face is registered yet. Turn on Face-Lock in Settings first.")
    owner_encoding = np.load(config.FACE_DATA_PATH, allow_pickle=False)
    new_encoding = get_face_encoding(image_bytes)
    distance = float(face_recognition.face_distance([owner_encoding], new_encoding)[0])
    return distance <= MATCH_TOLERANCE, distance


# Quick check with two photos:  python face_lock.py owner.jpg other.jpg
if __name__ == "__main__":
    import sys
    if not FACE_LIBRARIES_AVAILABLE:
        print("Face libraries not installed (see README section 'Face-Lock').")
    elif len(sys.argv) == 3:
        with open(sys.argv[1], "rb") as first, open(sys.argv[2], "rb") as second:
            encoding_1 = get_face_encoding(first.read())
            encoding_2 = get_face_encoding(second.read())
        distance = face_recognition.face_distance([encoding_1], encoding_2)[0]
        print(f"Distance: {distance:.3f} -> {'SAME person' if distance <= MATCH_TOLERANCE else 'DIFFERENT person'}")
    else:
        print("Face libraries are installed. Usage: python face_lock.py photo1.jpg photo2.jpg")
