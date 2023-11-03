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
    if not os.path.exists(sys.argv[1]):
        print('Err path!')
        return
    files = os.listdir(sys.argv[1])
    
    # Если JSON файлы не существуют, записать их
    if not has_json_files(sys.argv[1]):
        tasks = []
        for file in files:
            if '.wav' in file:
                tasks.append(recognize(sys.argv[1]+'/'+file))

        # Ограничение на количество одновременно запущенных задач (например, 5)
        sem = asyncio.Semaphore(5)

        async def process_with_semaphore(task):
            async with sem:
                return await task

        await asyncio.gather(*(process_with_semaphore(task) for task in tasks))

    # Независимо от того, были ли созданы JSON файлы или нет, извлеките текст и удалите файлы JSON
    extract_all_phrase_to_text(sys.argv[1])

    
def has_json_files(directory):
    """Проверяет директорию на наличие файлов с расширением .json."""
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
        
def extract_all_phrase_to_text(directory):
    all_phrases = []
    
    # Извлечение 'all_phrase' из каждого файла
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            with open(os.path.join(directory, filename), 'r', encoding='utf-8') as file:
                data = json.load(file)
                for entry in data:
                    if 'all_phrase' in entry:
                        all_phrases.append(entry['all_phrase'])

    # Добавление извлеченных фраз в существующий текстовый файл (или создание нового, если он не существует)
    with open(os.path.join(directory, 'all_phrases.txt'), 'a', encoding='utf-8') as file:  # Используйте 'a' для добавления
        for phrase in all_phrases:
            if phrase.strip():  # Исключение пустых строк
                file.write(f"1 {phrase}\n")

    # Удаление исходных файлов JSON
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            os.remove(os.path.join(directory, filename))

            
    
asyncio.run(read_dir())

