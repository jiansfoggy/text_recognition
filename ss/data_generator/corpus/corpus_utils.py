import string, os, random

def get_single_word_from_composed_word(corpus_path):
    #gen single word from tu ghep
    all_text = open(corpus_path, 'r')
    final_list=[]
    count=0
    for line in all_text.readlines():
        sub_str=(line.replace('\n','')).split(' ')
        for str in sub_str:
            if str not in final_list:
                count+=1
                print(count,':',str)
                final_list.append(str)
    final_text=''
    for line in final_list:
        final_text+=line+'\n'

    #list_text = [line.split(' ') for line in all_text.readlines()]
    with open("data/corpus/Viet22k_single.txt", "w") as save_file:
       save_file.write(final_text)
    print("Done")

def gen_random_serial_corpus(num_to_gen=1000, max_length=15):  #generate serial
    print("gen_random_serial_corpus",num_to_gen,max_length)
    final_text=''
    for i in range(num_to_gen):
        length_of_word=random.randint(2,max_length)
        lower=random.choice([True, False])
        if lower:
            line=''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length_of_word))
        else:
            line=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length_of_word))
        final_text+=line+'\n'

    with open("random_serial_"+str(num_to_gen)+".txt", "w") as save_file:
       save_file.write(final_text)
    print("Done")

def gen_random_number_corpus(num_to_gen=1000, max_length=12): #generate number with/without dot or comma
    print("gen_number_corpus",num_to_gen,max_length)
    final_text = ''
    for i in range(num_to_gen):
        length_of_word=random.randint(1,max_length)
        line = ''.join(random.choice(string.digits))+''.join(random.choice('.,0123456789.,'))+''.join(random.choice(string.digits) for _ in range(length_of_word))
        final_text += line + '\n'

    with open("random_number_" + str(num_to_gen) + ".txt", "w") as save_file:
        save_file.write(final_text)

def gen_random_symbol_corpus(num_to_gen=300, max_length=4): #generate symbol
    print("gen_number_corpus",num_to_gen,max_length)
    symbol_char = '*:,@$.-(#%\'\")/~!^&_+={}[]\;<>?※”'
    symbol_char_list = [x for x in symbol_char]
    final_text = ''
    for i in range(num_to_gen):
        length_of_word=random.randint(1,max_length)
        line = ''.join(random.choice(symbol_char_list)  for _ in range(length_of_word))
        final_text += line + '\n'

    with open("random_symbol_" + str(num_to_gen) + ".txt", "w") as save_file:
        save_file.write(final_text)

def gen_final_corpus(corpus_dir=''):
    print('corpus_utils.gen_final_corpus')
    file_list=[
        'English10k.txt',
        'Viet_4518_single.txt',
        'Viet_1474_no_accent.txt',
        'Abbreviation.txt',
        'Additional.txt',
        'random_number_1000.txt',
        'random_serial_1000.txt',
        'random_symbol_300.txt'
    ]
    final_corpus=[]
    for file in file_list:
        gen_triple=True
        if 'number' in file or 'symbol' in file:
            gen_triple=False
        all_text = open(os.path.join(corpus_dir,file), 'r', encoding='utf-8')
        for line in all_text.readlines():
            sub_str = line.replace('\n', '')
            final_corpus.append(sub_str.lower())
            if gen_triple: #generate uppercase and word with 1st uppercase
                str_upper=sub_str.upper()
                final_corpus.append(str_upper)
                first_char=sub_str[0]
                first_char_upper=first_char.upper()
                str_first_char_upper=first_char_upper+sub_str[1:]
                final_corpus.append(str_first_char_upper)

    final_str=''
    count = 0
    random.shuffle(final_corpus)
    for corpus in final_corpus:
        count+=1
        print(count,corpus)
        final_str+=corpus+'\n'

    save_filename=os.path.join(corpus_dir,'final_corpus_31Jan.txt')
    print('Save corpus:',save_filename)
    with open(save_filename, "w", encoding='utf-8') as save_file:
        save_file.write(final_str)
    return save_filename


if __name__== "__main__":
    #gen_random_serial_corpus()
    #gen_random_number_corpus()
    #gen_random_symbol_corpus()
    gen_final_corpus()