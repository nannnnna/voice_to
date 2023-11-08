import asyncio
import websockets
import sys
import wave
import os
import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('input_folder', type=str, help='Путь к директории с аудиофайлами')
parser.add_argument('output_file', type=str, help='Путь к файлу для записи результатов')
args = parser.parse_args()
uri_ws = 'ws://95.216.166.56:2700'
# uri_ws = 'ws://localhost:2700'

async def read_dir():
    if len(sys.argv) == 1: 
        print('Invalid arg')
        return
    if not os.path.exists(args.input_folder):
        print('Err path!')
        return
    if os.path.isfile(args.output_file):
        print(f"{args.output_file} является файлом")
    else:
        print(f"{args.output_file} не является файлом")
    
    files = os.listdir(args.input_folder) 
    
    # Если JSON файлы не существуют, записать их
    if not has_json_files(args.output_file):
        tasks = []
        for file in files:
            if '.wav' in file:
                tasks.append(recognize(os.path.join(args.input_folder, file)))

        sem = asyncio.Semaphore(5)

        async def process_with_semaphore(task):
            async with sem:
                return await task

        await asyncio.gather(*(process_with_semaphore(task) for task in tasks))

    
    extract_all_phrase_to_text(sys.argv[1])

    
def has_json_files(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            return True
    return False

      
async def recognize(file):
    async with websockets.connect(uri_ws) as websocket:
        print('---start ' + file +'---')
        vosk_result = []
        wf = wave.open(file, "rb")
        await websocket.send('{ "config" : { "sample_rate" : %d } }' % (wf.getframerate()))
        buffer_size = int(wf.getframerate() * 0.2) # 0.2 seconds of audio
        while True:
            data = wf.readframes(buffer_size)

            if len (data)== 0:
                break

            await websocket.send(data)
            data = json.loads(await websocket.recv())

            if 'result' in data:
                vosk_result.append(data)

        await websocket.send('{"eof" : 1}')
        vosk_result.append(json.loads(await websocket.recv())) 
        
        await write_data(vosk_result, file)
        print('---end ' + file +'---')

async def write_data(data, file_name):
    write_data = []
    for result in data:
        if isinstance(result, str):
            result = json.loads(result)
        words = []
        if 'result' in result:
            if isinstance(result, str):
                result = json.loads(result)
            for res in result['result']: 
             words.append(res['word'])
        if 'text' in result:
            write_data.append({
                'words': words,
                'text': result['text']
            })
    write_data.append({
        'all_phrase': ', '.join([w['text'] for w in write_data])
    })
    file_name = file_name[:file_name.find('.')] + '.json'
    with open(file_name, "w", encoding="utf-8") as file:
        json.dump(write_data, file, ensure_ascii=False, indent=4)
        
def extract_all_phrase_to_text(output_file):
    all_phrases = []
    
    for filename in os.listdir(output_file):
        if filename.endswith('.json'):
            with open(os.path.join(output_file, filename), 'r', encoding='utf-8') as file:
                data = json.load(file)
                for entry in data:
                    if 'all_phrase' in entry:
                        all_phrases.append(entry['all_phrase'])
    
    with open(output_file, 'a', encoding='utf-8') as file:
        for phrase in all_phrases:
            if phrase.strip(): 
                file.write(f"1 {phrase}\n")
    
    # Удаление исходных файлов JSON
    for filename in os.listdir(output_file):
        if filename.endswith('.json'):
            os.remove(os.path.join(output_file, filename))

            
    
asyncio.run(read_dir())

