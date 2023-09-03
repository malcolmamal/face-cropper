import dlib
from PIL import Image, UnidentifiedImageError
from pathlib import Path
import face_recognition
import os
import time
import logging
import argparse

# globals

APP_VERSION = '0.0.1'
CURRENT_DIRNAME = os.path.dirname(__file__)

tmp_file_path = f'{CURRENT_DIRNAME}/tmp.png'
target_path = ''

baseline_image = None
baseline_image_encoding = None

resolution = 512
upscale = False

skipped_files = []

def initialize_logger():
    log_path = os.path.join(CURRENT_DIRNAME, 'logs')
    if not os.path.exists(log_path):
        os.makedirs(log_path)

    logger = logging.getLogger("cropper")
    logger.setLevel(logging.DEBUG)
    log_handler = logging.FileHandler('logs/cropper.log')
    log_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    return logger

def fill_baseline_image(image_path):
    global baseline_image
    global baseline_image_encoding

    loaded_image = face_recognition.load_image_file(image_path)
    encodings = (face_recognition.face_encodings(loaded_image))
    if len(encodings) == 0:
        print("WARNING: Somehow there were no face encodings even though there was one face location found")
        return

    baseline_image = loaded_image
    baseline_image_encoding = face_recognition.face_encodings(baseline_image)[0]


def pick_best_face_locations(image, face_locations):
    print('Going to pick best face locations out of', len(face_locations))
    global baseline_image_encoding
    global tmp_file_path

    for locations in face_locations:
        (top, right, bottom, left) = locations

        # offsets needed otherwise the face might not be found again
        temp_image = image.crop((left-50, top-50, right+50, bottom+50))
        temp_image.save(tmp_file_path, 'PNG')
        candidate_image = face_recognition.load_image_file(tmp_file_path)

        candidate_encodings = face_recognition.face_encodings(candidate_image)
        if not candidate_encodings:
            print('Warning! Somehow found no candidate encodings!')
            continue

        try:
            if baseline_image_encoding and face_recognition.compare_faces([baseline_image_encoding], candidate_encodings[0])[0]:
                print('Found matching face in locations: ', locations)

                # TODO: we will likely need to iterate over all and collect face_recognition.face_distance()
                #       and take the one with lowest distance value

                return [locations]
        except ValueError:
            # TODO: something weird is going on, need to investigate (biancablanchard test data)
            print('TODO: WTF is going on here?')
            return []

    print('Found no matching faces!')
    # TODO: consider returning on of the candidates (biggest? first from the left? first from the array?)
    #       investigate more why there are so many "not found" (how many found in multiple vs not found)
    #       as first step - just log the filenames for manual recheck to see what is going on
    return []


def crop_image(person, full_path):
    global baseline_image, skipped_files, upscale, resolution

    filename = Path(full_path).name
    filename_without_extension = filename.split('.')[0]

    image = None
    try:
        image = Image.open(full_path)
    except UnidentifiedImageError:
        print(f'Unsupported format found in {full_path}')
        return
    except OSError as e:
        if 'Truncated File Read' in str(e):
            print(f'Invalid data in {full_path}')
            return

    original_width, original_height = image.size
    if original_width < resolution or original_height < resolution:
        if not upscale:
            print(f'file too small, but no upscale - skipping { full_path }')
            return

        # TODO: also decide when an image is too small for up-scaling to not bother with those

        print('upscale needed')

        # will upscale original image
        new_width = resolution if original_width < resolution else original_width
        new_height = resolution if original_height < resolution else original_height
        if original_width > original_height:
            new_width = original_width * new_height / original_height
        else:
            new_height = original_height * new_width / original_width

        upscaled_image = image.resize((int(new_width), int(new_height)))

        directory = os.path.join(target_path, 'resized', person)
        if not os.path.exists(directory):
            os.makedirs(directory)

        upscaled_path = r'{}\{}_{}.png'.format(directory, filename_without_extension, 'resized')
        upscaled_image.save(upscaled_path, 'PNG')
        image = upscaled_image
        original_width, original_height = image.size
        full_path = upscaled_path

    fr_image = face_recognition.load_image_file(full_path)
    # TODO: check VRAM and try to compute what would be the max resolution (width * height) before running out of VRAM
    try:
        face_locations = face_recognition.face_locations(fr_image, number_of_times_to_upsample=0, model="cnn")
    except RuntimeError as e:
        print('Image was probably too big, cannot handle it so, skipping now')
        # TODO: workaround - resize (downsize) and try again instead of returning
        if 'out of memory' in str(e):
            print('!!! It was indeed out of memory error', str(e))
        return

    found_faces = len(face_locations)
    print("I found {} face(s) in this photograph {}.".format(len(face_locations), filename))
    # print('locations', face_locations)
    # face_locations = [(274, 1134, 613, 794)]

    if not found_faces:
        print('Found NO faces!')
        return
    elif found_faces == 1:
        print('Found one face!')
        if baseline_image is None:
            print('There was no baseline image, setting to this image')
            fill_baseline_image(full_path)
    else:
        print('Found multiple faces: ', found_faces)
        face_locations = pick_best_face_locations(image, face_locations)
        if not len(face_locations):
            skipped_files.append(full_path)
            print('Found no locations after going through multiple faces')
            return

    (top, right, bottom, left) = face_locations[0]

    print('size is {}x{}'.format(original_width, original_height))

    was_expanded = False

    print('original', left, right, top, bottom)

    # in case the face is small, let's expand the image so the size will be at least 512 as we want to avoid up-scaling
    if right - left < resolution:
        remaining = resolution - (right - left)
        half = remaining // 2
        left -= half
        right += half
        if right - left == resolution - 1:
            right += 1

        print('remaining horizontal', remaining, remaining / resolution)
        if remaining / resolution > 0.4:
            # we do not consider small expansion as expanded
            was_expanded = True
    else:
        print('horizontal was fine')

    if bottom - top < resolution:
        remaining = resolution - (bottom - top)
        half = remaining // 2
        top -= half
        bottom += half
        if bottom - top == resolution - 1:
            bottom += 1

        print('remaining vertical', remaining, remaining / resolution)
        if remaining / resolution > 0.4:
            # we do not consider small expansion as expanded
            was_expanded = True
    else:
        print('vertical was fine')

    print('was expanded', was_expanded)

    print('after expanded', left, right, top, bottom)

    # if there is discrepancy it will be due to rounding issues, let's fix that
    if right - left > bottom - top:
        bottom += (right - left) - (bottom - top)
    elif right - left < bottom - top:
        right += (bottom - top) - (right - left)

    print('after discrepancy fix', left, right, top, bottom)

    # if the positions are outside of image, move the image
    if top < 1:
        bottom += abs(top)
        top = 1

    if left < 1:
        right += abs(left)
        left = 1

    if right > original_width:
        left = original_width - resolution
        right = original_width

    if bottom > original_height:
        top = original_height - resolution
        bottom = original_height

    print(left, right, top, bottom)
    print("res is {}x{}".format(right - left, bottom - top))

    used_boundaries = []
    ratios = {'fifth': 0.2, 'third': 0.33, 'half': 0.5, 'half_raised': 0.5}

    for prefix, expand_ratio in ratios.items():
        final_right = right
        final_left = left
        final_top = top
        final_bottom = bottom

        name_suffix = prefix

        # when we know it was expanded, we already know the head was too small, so no need to expand further
        if was_expanded:
            # we only do it for the first dictionary iteration as the effect will be the same for all
            if prefix != 'fifth':
                continue
            name_suffix = 'default'
            print('was already expanded, not expanding further')
        # we didn't expand the image, so it was big enough, but we need to move further back
        # since the algorith considers inner face mainly, and we want full headshot
        else:
            expand_by = int((right - left) * expand_ratio)
            print('expand_by', expand_by)
            if left > expand_by and right + expand_by < original_width \
                    and top > expand_by and bottom + expand_by < original_height:
                # we can expand in all directions freely
                final_left -= expand_by
                final_right += expand_by
                final_top -= expand_by
                final_bottom += expand_by
                print('expanding evenly in all directions!', expand_ratio)
            elif right - left + expand_by * 2 < original_width \
                    and bottom - top + expand_by * 2 < original_height:
                # we know we can expand but not evenly in all directions, so we need to check for it
                if left > expand_by and original_width - right > expand_by:
                    final_left -= expand_by
                    final_right += expand_by
                elif left > expand_by:
                    allowed_right = original_width - right
                    final_right = original_width
                    final_left -= expand_by * 2 - allowed_right
                else:
                    allowed_left = left - 1
                    final_left = 1
                    final_right += expand_by * 2 - allowed_left

                if top > expand_by and original_height - bottom > expand_by:
                    final_top -= expand_by
                    final_bottom += expand_by
                elif top > expand_by:
                    allowed_bottom = original_height - bottom
                    final_bottom = original_height
                    final_top -= expand_by * 2 - allowed_bottom
                else:
                    allowed_top = top - 1
                    final_top = 1
                    final_bottom += expand_by * 2 - allowed_top

                print('expanding smart in some directions!', expand_ratio)
            elif right - left + expand_by * 2 > original_width \
                    and original_width <= original_height:
                # we know we can expand but not fully, so we need to figure out max expansion length
                expand_by = (original_width - right + left) // 2

                if left > expand_by and original_width - right > expand_by:
                    final_left -= expand_by
                    final_right += expand_by
                elif left > expand_by:
                    allowed_right = original_width - right
                    final_right = original_width
                    final_left -= expand_by * 2 - allowed_right
                else:
                    allowed_left = left - 1
                    final_left = 1
                    final_right += expand_by * 2 - allowed_left

                if top > expand_by and original_height - bottom > expand_by:
                    final_top -= expand_by
                    final_bottom += expand_by
                elif top > expand_by:
                    allowed_bottom = original_height - bottom
                    final_bottom = original_height
                    final_top -= expand_by * 2 - allowed_bottom
                else:
                    allowed_top = top - 1
                    final_top = 1
                    final_bottom += expand_by * 2 - allowed_top

                print('expanding smart in some directions with max horizontal!', expand_ratio)
            else:
                print('not expanding')
                pass
                # 13(68)_half.png - perhaps it should be expanded by it could not be expanded THAT much
                # (because of horizontal)

        # half_raised is not only expanded but also raised by 1/10
        if prefix == 'half_raised':
            offset = (final_bottom - final_top) // 10
            if final_top > offset:
                final_top -= offset
                final_bottom -= offset

        boundary = '{}_{}_{}_{}'.format(final_left, final_right, final_top, final_bottom)
        if boundary in used_boundaries:
            print('The following boundary {} from prefix {} was already used. Skipping'.format(boundary, prefix))
            continue

        used_boundaries.append(boundary)

        # cropped_image = image.crop((x, y, x+w, y+h))
        print('resolution to crop', final_left, final_right, final_top, final_bottom)
        cropped_image = image.crop((final_left, final_top, final_right, final_bottom))

        # at this point we should have a square,
        # so we can just check if one dimension is too long, and we need to downscale
        if top - left != resolution:
            cropped_image = cropped_image.resize((resolution, resolution))

        directory = os.path.join(target_path, 'cropped', person)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # save the cropped image
        try:
            cropped_image.save(r'{}\{}_{}.png'.format(directory, filename_without_extension, name_suffix), 'PNG')
        except OSError as e:
            if 'cannot write mode' in str(e):
                cropped_image = cropped_image.convert('RGB')
                cropped_image.save(r'{}\{}_{}.png'.format(directory, filename_without_extension, name_suffix), 'PNG')


def run_cropping(main_path, person_name):
    input_path = os.path.join(main_path, person_name)
    print('inputPath', input_path, 'personName', person_name)
    for root, dirs, files in os.walk(input_path):
        quantity = len(files)
        i = 0
        for name in files:
            i += 1
            start_time = time.time()
            crop_image(person_name, os.path.join(root, name))
            print("--- {} seconds when processing {} ---".format(time.time() - start_time, name))
            print('done {}/{}'.format(i, quantity))
            print('-' * 20)


def main():
    global baseline_image, baseline_image_encoding, resolution, upscale, target_path, logger
    # TODO: use the logger instead of print
    logger = initialize_logger()

    parser = argparse.ArgumentParser(description="Script to crop faces at various resolutions")
    # parser.add_argument('--config', default='configs/config.json', help="Path to the config file")
    parser.add_argument('--resolution', '-r', default='512',
                        help="Cropping resolution, suggested values: 512, 768, 1024")
    parser.add_argument('--source-path', '-sp', default=r"C:\!PhotosForAI\autocrop",
                        help="Source folder with people subfolders")
    parser.add_argument('--target-path', '-tp', default=r"C:\!PhotosForAI\output", help="Target folder for the outputs")
    parser.add_argument('--debug', '-d', action='store_true', help="Show additional data in console")
    parser.add_argument('--check-dlib', '-cd', action='store_true', help="Check if DLIB is using CUDA")
    parser.add_argument('--version', '-v', action='store_true')

    args = parser.parse_args()

    if args.debug:
        print(f"\nArguments: {args}")

    if args.version:
        print(f'Version: {APP_VERSION}')
        exit(0)

    if args.check_dlib:
        print('dlib using cuda:', dlib.DLIB_USE_CUDA)
        exit(0)

    if args.source_path:
        if not os.path.exists(args.source_path):
            raise Exception("Source path does not exist!", args.source_path)
        source_path = args.source_path
    else:
        raise Exception("Missing source path!")

    if args.target_path:
        if not os.path.exists(args.target_path):
            raise Exception("Target path does not exist!", args.target_path)
        target_path = args.target_path
    else:
        raise Exception("Missing target path!")

    if args.resolution and args.resolution.isnumeric():
        resolution = int(args.resolution)
    else:
        resolution = 512

    upscale = False if resolution == 512 else True

    print('Starting cropping!')
    global_start_time = time.time()

    for item in os.listdir(source_path):
        if os.path.isdir(os.path.join(source_path, item)):
            # reset baseline image
            baseline_image = None
            baseline_image_encoding = None

            if os.path.isfile(tmp_file_path):
                fill_baseline_image(tmp_file_path)

            print('Running for', item)
            run_cropping(source_path, item)

    if os.path.isfile(tmp_file_path):
        os.remove(tmp_file_path)
        print('Removed the tmp image file')

    print('Skipped files', skipped_files)
    print('Finished cropping!')
    print("--- {} seconds passed for all ---".format(time.time() - global_start_time))


if __name__ == "__main__":
    main()

# TODO: put in proper folders

# TODO: new features / fixes
# 1. switch to crop more than just the face
# 2. non square resolutions (i.e. 512x768)
# 3. make sure the tmp.png file works correctly

# known_image = face_recognition.load_image_file("biden.jpg")
# unknown_image = face_recognition.load_image_file("someone.jpg")
#
# biden_encoding = face_recognition.face_encodings(known_image)[0]
# unknown_encoding = face_recognition.face_encodings(unknown_image)[0]
#
# results = face_recognition.compare_faces([biden_encoding], unknown_encoding)
# print(results)
