
def receive_dict_function(input:dict)->dict:
    return input

def copy_dict(copy_dict:dict)->dict:
    new_dict = dict(copy_dict)
    return new_dict

if __name__ == '__main__':
    aa={"name":"dby","age":18}
    one = copy_dict(receive_dict_function(aa))
    # 对返回的new_dict字典再次进行一次拷贝，是一次浅拷贝
    two = dict(copy_dict(receive_dict_function(aa)))
    print(one)
    print(two)
    print(id(one))
    print(id(two))

