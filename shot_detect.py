#!/usr/bin/env python3
import argparse
import sys, os
import math
import json
import subprocess
import codecs
from pathlib import Path

from google.cloud import videointelligence_v1 as videointelligence
import google.auth.exceptions

ANALYSIS_NUM_SLOTS = 100

def err(*a, **k):
    print('\033[31m\033[1m', end='', file=sys.stderr)
    print('Error:', *a, **k, file=sys.stderr)
    print('\033[0m', end='', file=sys.stderr)

def get_folder_name(path: str) -> str:
    return path.replace('gs://', 'gs--').replace('/', '--')

def pts_to_timestamp(pts: float, precision: float=10e1) -> str:
    ms = int((pts - math.floor(pts)) * precision)
    pts_s = math.floor(pts)
    s = pts_s % 60
    m = math.floor(pts_s / 60) % 60
    h = math.floor(pts_s / 60 / 60)

    return f'{h:01d}:{m:02d}:{s:02d}.{ms:02d}'

def timestamp_to_pts(timestamp: str) -> float:
    time, ms = timestamp.split('.')
    pts = int(ms) / (10 ** len(ms))
    h, m, s = time.split(':')
    pts += int(s)
    pts += int(m) * 60
    pts += int(h) * 60 * 60
    return pts

class App:
    def __init__(self):
        pass

    def cleanup(self):
        pass

    def init_api(self):
        self.client = videointelligence.VideoIntelligenceServiceClient()
        self.features = [videointelligence.Feature.SHOT_CHANGE_DETECTION]

    def action_verify(self, args):
        try:
            self.init_api()
        except google.auth.exceptions.DefaultCredentialsError:
            exit(1)
        print('OK')

    def action_detect(self, args):
        if args.uri is None or len(args.uri) == 0:
            err("--uri to video is required")
            exit(1)

        uri = args.uri
        folder = get_folder_name(uri)
        model = args.model or 'builtin/stable'

        print(f'Shot change detection starting on URI: {uri}')
        self.init_api()
        operation = self.client.annotate_video(
            request={
                "features": self.features,
                "input_uri": uri,
                "video_context": {
                    "shot_change_detection_config": {
                        "model": model,
                    },
                },
            }
        )
        print(f"Using model: {model}")

        print()
        print("Processing video for shot change annotations...")
        print("This may take up to 30 minutes, please wait")
        result = operation.result(timeout=1800)

        shots = []
        for i, shot in enumerate(result.annotation_results[0].shot_annotations):
            start_time = (
                shot.start_time_offset.seconds + shot.start_time_offset.microseconds / 1e6
            )
            end_time = (
                shot.end_time_offset.seconds + shot.end_time_offset.microseconds / 1e6
            )

            shots.append({
                "shot_id": str((i + 1) * 10),
                "start_pts": start_time,
                "end_pts": end_time,
            })

        data = {
            "uri": uri,
            "model": model,
            "source": "original",
            "shots": shots,
        }

        # print(data)

        directory = f"./data/{folder}"
        Path(directory).mkdir(parents=True, exist_ok=True)

        filename = f"{directory}/original_{model.replace('/', '-')}.json"
        with open(filename, "w") as f:
            json.dump(data, f)

        print()
        print("Detection completed!")
        print(f"Data written to '{filename}'")

    def action_correct(self, args):
        if args.uri is None or len(args.uri) == 0:
            err("--uri to video is required")
            exit(1)

        uri = args.uri
        folder = get_folder_name(uri)

        directory = Path("./data") / Path(folder)
        if not directory.exists():
            err("""No shot change detection data found for this URI!
Please run the detection function for this video first if you haven't done it.""")
            exit(1)

        originals = [f for f in directory.glob('**/original_*.json') if f.is_file()]
        for original in originals:
            original_name = original.stem.split('_')[1]
            original_name_unescaped = original_name.replace('-', '/')

            overlay_path = directory / Path(f"OVERLAY_{original_name}.txt")
            if overlay_path.exists() and overlay_path.is_file():
                print(f"An OVERLAY file '{overlay_path.as_posix()}' already exists.")
                print('\033[33m\033[1m', end='')
                result = input('Overwrite with newly generated OVERLAY file? [y/N] > \033[0m')
                if not result.lower() == 'y':
                    continue

            print(f"Generating OVERLAY for '{original_name_unescaped}'...")
            with open(original.as_posix(), 'r') as f:
                data = json.load(f)

            with open(overlay_path, 'w') as f:
                f.write(f"# This is an OVERLAY file for '{uri}' ({original_name_unescaped})\n")
                f.write("# Use this file to edit the shot change detection data.\n\n")
                f.write("# The format for each action is in the following line with (F: ...)\n\n")
                f.write("# keep      - do not modify, keep this shot as-is\n")
                f.write("#             (F: keep)\n\n")
                f.write("# split     - insert a cut between the previous and the next shot\n")
                f.write("#             (F: split [new_shot_id] [timecode_to_cut])\n\n")
                f.write("# mergeup   - delete this shot, set the previous shot's out point to this shot's out point\n")
                f.write("#             (F: mergeup)\n\n")
                f.write("# mergedown - delete this shot, set the next shot's in point to this shot's in point\n")
                f.write("#             (F: mergedown)\n\n")
                f.write("# edit      - edit this shot's ID or in/out timestamp\n")
                f.write("#             (F: edit [shot_id] [in_timestamp] -> [out_timestamp])\n\n")
                f.write("# add       - add a new shot, set your own ID and in/out timestamp\n")
                f.write("#             (F: add [new_shot_id] [in_timestamp] -> [out_timestamp])\n\n")
                f.write("# delete    - delete this shot, neighboring shots won't be modified\n")
                f.write("#             (F: delete)\n")
                f.write("\n")
                for shot in data['shots']:
                    f.write(f"keep {shot['shot_id']} {pts_to_timestamp(shot['start_pts'])} -> {pts_to_timestamp(shot['end_pts'])}\n")

        subprocess.call(['open', directory])
        print('\nEdit the OVERLAY file(s) and save it')
        print('\033[33m\033[1mAfter editing, press enter here to continue...\033[0m')
        input()

        for original in originals:
            original_name = original.stem.split('_')[1]
            with open(original.as_posix(), 'r') as f:
                original_data = json.load(f)

            shots = []
            ptr = 0

            overlay_path = directory / Path(f"OVERLAY_{original_name}.txt")
            with open(overlay_path, 'r') as f:
                lines = f.read().splitlines()

            mergedown = None
            clean = True
            for line in lines:
                line_stripped = line.strip()
                if len(line_stripped) == 0:
                    continue

                if line[0] == '#':
                    continue

                segments = line.split()
                action = segments[0]
                segments = segments[1:]
                # action, shot_id, start_ts, _, end_ts = line.split()

                #print(original_data['shots'][ptr]['shot_id'], shot_id)
                #if not action == 'edit':
                #    assert original_data['shots'][ptr]['shot_id'] == shot_id

                if mergedown:
                    clean = False
                    shots.append({
                        **original_data['shots'][ptr],
                        "start_pts": mergedown['start_pts'],
                    })
                    ptr += 1
                    mergedown = None
                    continue

                if action == 'keep':
                    shots.append(original_data['shots'][ptr])
                elif action == 'edit':
                    clean = False
                    shot_id, start_ts, _, end_ts = segments
                    shots.append({
                        "shot_id": shot_id,
                        "start_pts": timestamp_to_pts(start_ts),
                        "end_pts": timestamp_to_pts(end_ts),
                    })
                elif action == 'add':
                    clean = False
                    shot_id, start_ts, _, end_ts = segments
                    shots.append({
                        "shot_id": shot_id,
                        "start_pts": timestamp_to_pts(start_ts),
                        "end_pts": timestamp_to_pts(end_ts),
                    })
                    ptr -= 1
                elif action == 'mergeup':
                    clean = False
                    if len(shots) == 0:
                        err('Cannot mergeup to nothing!')
                        exit(1)
                    shots[-1]["end_pts"] = original_data['shots'][ptr]["end_pts"]
                elif action == 'mergedown':
                    try:
                        original_data['shots'][ptr + 1]
                        mergedown = original_data['shots'][ptr]
                    except IndexError:
                        err('Cannot mergedown to nothing!')
                        exit(1)
                elif action == 'delete':
                    clean = False
                elif action == 'split':
                    clean = False
                    if len(shots) == 0:
                        err('Cannot split from no previous shot!')
                        exit(1)

                    shot_id, cut_ts = segments
                    this_shot = {
                        "shot_id": shot_id,
                        "start_pts": timestamp_to_pts(cut_ts),
                        "end_pts": shots[-1]["end_pts"],
                    }
                    shots[-1]["end_pts"] = timestamp_to_pts(cut_ts)
                    shots.append(this_shot)
                    ptr -= 1
                else:
                    err(f"Unknown action '{action}'")
                    exit(1)

                ptr += 1

            with open(directory / Path(f"corrected_{original_name}.json"), 'w') as f:
                json.dump(
                    {
                        **original_data,
                        'shots': shots,
                        'source': 'correction' if not clean else 'original_untouched',
                    },
                    f,
                )

        print('Corrected file(s) was saved!')

    def action_preview(self, args):
        if args.uri is None or len(args.uri) == 0:
            err("--uri to video is required")
            exit(1)

        uri = args.uri
        folder = get_folder_name(uri)

        directory = Path("./data") / Path(folder)
        if not directory.exists():
            err("""No shot change detection data found for this URI!
Please run the detection function for this video first if you haven't done it.""")
            exit(1)

        sub_template = """[Script Info]
Title: Preview
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 853
PlayResY: 480

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ShotA,Arial,28,&H00A9A9FF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,2,0,8,10,10,10,1
Style: ShotB,Arial,28,&H00AAFFAE,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,2,0,8,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        files = [f for f in directory.glob('**/corrected_*.json') if f.is_file()]
        if len(files) == 0:
            files = [f for f in directory.glob('**/original_*.json') if f.is_file()]

        for file in files:
            file_name = file.stem.split('_')[1]
            with open(file.as_posix(), 'r') as f:
                file_data = json.load(f)

            sub_path = directory / Path(f"preview_{file_name}.ass")
            with open(sub_path, 'w') as f:
                f.write(sub_template)
                for i, shot in enumerate(file_data['shots']):
                    style = 'ShotA' if i % 2 == 0 else 'ShotB'
                    start_ts = pts_to_timestamp(shot['start_pts'])
                    end_ts = pts_to_timestamp(shot['end_pts'])
                    prefix = f"Dialogue: 0,{start_ts},{end_ts},{style},,0,0,0,,"
                    f.write(f"{prefix}SHOT {shot['shot_id']}\n")
                    f.write(f"{prefix}{start_ts} ▶ {end_ts}\n")

            print(f"Preview subtitle successfully exported for '{sub_path}'")

        subprocess.call(['open', directory])

    def action_export(self, args):
        if args.uri is None or len(args.uri) == 0:
            err("--uri to video is required")
            exit(1)

        uri = args.uri
        folder = get_folder_name(uri)

        directory = Path("./data") / Path(folder)
        if not directory.exists():
            err("""No shot change detection data found for this URI!
Please run the detection function for this video first if you haven't done it.""")
            exit(1)

        files = [f for f in directory.glob('**/corrected_*.json') if f.is_file()]
        if len(files) == 0:
            files = [f for f in directory.glob('**/original_*.json') if f.is_file()]

        print("\033[36m\033[1m", end='')
        print("EXPORT RESULT CSV")
        print("\033[0m", end='')
        print(f"Shot change statistics for URI '{uri}' is being processed...\n")
        print('The program will calculate and generate the CSV result for these entries:')

        last_pts = 0
        for file in files:
            with open(file.as_posix(), 'r') as f:
                data = json.load(f)
            ty = '\033[33moriginal AI detected data'
            if data['source'] == 'correction':
                ty = '\033[35mmanually corrected data'
            print("\033[32m", end='')
            print(f"- Model \033[1m{data['model']}\033[0m\033[32m using {ty}\033[0m")

            end_pts = data['shots'][-1]['end_pts']
            if end_pts > last_pts:
                last_pts = end_pts

        print('\nHowever, in order to do the calculations correctly, you need to input the total duration of this video.')
        print('You can use the following formats to enter the video duration:\n')
        print('    \033[1m01:23:45.00\033[0m  [timecode, rounded seconds]')
        print('    \033[1m01:23:45.78\033[0m  [timecode, milliseconds]')
        print('    \033[1m648.0\033[0m        [duration, rounded seconds]')
        print('    \033[1m648.798333\033[0m   [duration, precise seconds]')
        print()
        print(f'The ending timestamp of the last shot in this video is \033[36m{pts_to_timestamp(last_pts)}\033[0m')
        print()
        print('\033[33m\033[1mInput video duration > \033[0m', end='')
        duration = input()

        if ':' in duration:
            duration = timestamp_to_pts(duration)
        else:
            duration = float(duration)

        segment_duration = duration / ANALYSIS_NUM_SLOTS
        csv = [
            ['Filename', *(str(i + 1) for i in range(ANALYSIS_NUM_SLOTS))],
        ]

        for file in files:
            with open(file.as_posix(), 'r') as f:
                data = json.load(f)

            slots = [0 for _ in range(ANALYSIS_NUM_SLOTS)]

            current_segment = 0
            for shot in data['shots']:
                segment_end = (current_segment + 1) * segment_duration
                if shot['start_pts'] > segment_end:
                    current_segment += 1
                    segment_end = (current_segment + 1) * segment_duration

                slots[current_segment] += 1

            csv.append([
                f"\"{data['uri']} ({data['model']}; {'corrected' if data['source'] == 'correction' else 'automated'})\"",
                *(str(slot) for slot in slots),
            ])

        csv_str = '\n'.join(','.join(line) for line in csv)
        csv_path = directory / Path('RESULTS.csv')
        with codecs.open(csv_path.as_posix(), 'w', 'utf-8') as f:
            f.write(csv_str + '\n')

        print('\n\033[32m\033[1mCalculations complete!\033[0m')
        print('The results were saved to `RESULTS.csv`, you can now import this file into your spreadsheet processor.')

        subprocess.call(['open', directory])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action')
    parser.add_argument('--uri')
    parser.add_argument('--model')

    args = parser.parse_args()

    ACTION_PREFIX = 'action_'
    actions = [name[len(ACTION_PREFIX):] for name in dir(App) if name.startswith(ACTION_PREFIX)]

    if args.action not in actions:
        err('Action not found')
        exit(1)

    if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '').strip() == '':
        err('GOOGLE_APPLICATION_CREDENTIALS not set')
        exit(1)

    app = App()
    getattr(app, f'{ACTION_PREFIX}{args.action}')(args)
    app.cleanup()

if __name__ == "__main__":
    main()
