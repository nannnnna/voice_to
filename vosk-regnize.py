import asyncio
import websockets
import sys
import wave
import os
import json

uri_ws = 'ws://95.216.166.56:2700'
# uri_ws = 'ws://localhost:2700'

async def read_dir():
    if len(sys.argv) == 1: 
        print('Invalid arg')
        return
    if  not os.path.exists(sys.argv[1]):
        print('Err path!')
        return
    files = os.listdir(sys.argv[1])

    for file in files:
        if '.wav' in file:
           await recognize(sys.argv[1]+'/'+file)
      
async def recognize(file):
    async with websockets.connect(uri_ws) as websocket:
        print('---start ' + file +'---')
        vosk_result = []
        wf = wave.open(file, "rb")
        await websocket.send('{ "config" : { "sample_rate" : %d } }' % (wf.getframerate()))
        buffer_size = int(wf.getframerate() * 0.2) # 0.2 seconds of audio
        while True:
            data = wf.readframes(buffer_size)

            if len(data) == 0:
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
    
asyncio.run(read_dir())

