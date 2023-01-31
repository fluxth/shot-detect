#!/usr/bin/env python3
import argparse
import sys, os
import math
import json
import subprocess
from pathlib import Path

from google.cloud import videointelligence_v1 as videointelligence
import google.auth.exceptions

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

    return f'{h:01d}:{m:02d}:{s:02d}.{ms}'

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
                f.write("# Format:\n")
                f.write("# [action] [shot_id] [in_timestamp] -> [out_timestamp]\n\n")
                f.write("# keep      - do not modify, keep this shot as-is\n")
                f.write("# edit      - edit this shot's ID or in/out timestamp\n")
                f.write("# add       - add a new shot, set your own ID and in/out timestamp\n")
                f.write("# mergeup   - delete this shot, set the previous shot's out point to this shot's out point\n")
                f.write("# mergedown - delete this shot, set the next shot's in point to this shot's in point\n")
                f.write("# delete    - delete this shot, neighboring shots won't be modified\n")
                f.write("\n")
                for shot in data['shots']:
                    f.write(f"keep {shot['shot_id']} {shot['start_pts']:.6f} -> {shot['end_pts']:.6f}\n")

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

            mergedown = False
            for line in lines:
                line_stripped = line.strip()
                if len(line_stripped) == 0:
                    continue

                if line[0] == '#':
                    continue

                [action, shot_id, start_pts, _, end_pts] = line.split()

                #print(original_data['shots'][ptr]['shot_id'], shot_id)
                #if not action == 'edit':
                #    assert original_data['shots'][ptr]['shot_id'] == shot_id

                if mergedown:
                    shots.append({
                        **original_data['shots'][ptr],
                        "start_pts": original_data['shots'][ptr - 1]['start_pts'],
                    })
                    ptr += 1
                    mergedown = False
                    continue

                match action:
                    case 'keep':
                        shots.append(original_data['shots'][ptr])
                    case 'edit':
                        shots.append({
                            "shot_id": shot_id,
                            "start_pts": float(start_pts),
                            "end_pts": float(end_pts),
                        })
                    case 'add':
                        shots.append({
                            "shot_id": shot_id,
                            "start_pts": float(start_pts),
                            "end_pts": float(end_pts),
                        })
                        ptr -= 1
                    case 'mergeup':
                        if len(shots) == 0:
                            err('Cannot mergeup to nothing!')
                            exit(1)
                        shots[-1]["end_pts"] = original_data['shots'][ptr]["end_pts"]
                    case 'mergedown':
                        try:
                            original_data['shots'][ptr + 1]
                            mergedown = True
                        except IndexError:
                            err('Cannot mergedown to nothing!')
                            exit(1)
                    case 'delete':
                        pass
                    case _:
                        err(f"Unknown action '{action}'")
                        exit(1)

                ptr += 1

            with open(directory / Path(f"corrected_{original_name}.json"), 'w') as f:
                json.dump(
                    {
                        **original_data,
                        'shots': shots,
                        'source': 'correction',
                    },
                    f,
                )

        print('Corrected file(s) was saved!')

    def action_preview(self, args):
        # TODO: Generate ASS subtitles
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
        # TODO: Export to CSV
        err('This feature is not yet implemented!')
        exit(1)

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
