import concurrent.futures    # 用于类型标注
from general.base import db_process_base  # 用于类型标注
from concurrent.futures import ThreadPoolExecutor, as_completed


class scheduler:
    def __init__(self, node_list: list[db_process_base]):
        self.node_list = node_list
        self.node_map = self.process_name(self.node_list)
        
    def append(self):
        ...
    
    def run(self):
        ...
    
    @staticmethod
    def process_name(node_list: list[db_process_base]) -> dict[str, dict[str, int | list[str]]]:
        '''获取所有节点的名称和依赖'''
        node_map = {}
        for i, ch in enumerate(node_list):
            node_map[ch.name]["index"] = i
            node_map[ch.name]["next"] = ch.next_name
        return node_map
    
    def get_node():
        ...
    

def node_run(node_list: list[db_process_base]) -> None:
    '''启动线程池开始执行dag图'''
    node_map = process_name(node_list)
    with ThreadPoolExecutor() as tpool:
        running_tasks: list[concurrent.futures.Future] = []
        final_node = set()
        while True:
            run_node = get_node(final_node, node_map)
            # 如果获取不到可以执行的节点即退出
            if len(run_node) == 0:
                break
            # 将节点添加到线程池
            for ch in run_node:
                temp: db_process_base = node_list[node_map[ch]["index"]]
                running_tasks.append(tpool.submit(temp.run))
            # 等待10s看任务是否完成，未完成则更新新的任务进行执行
            for future in as_completed(running_tasks, timeout=5):
                final_node.add(future.result())


def process_name(node_list: list[db_process_base]) -> dict[str, dict[str, int | list[str]]]:
    '''获取所有节点的名称和依赖'''
    node_map = {}
    for i, ch in enumerate(node_list):
        node_map[ch.name]["index"] = i
        node_map[ch.name]["next"] = ch.next_name
    return node_map


def get_node(final_node: set, node_map: dict[str, dict[str, int | list[str]]]) -> list[int]:
    '''获取当前可以执行的节点'''
    run_node = []
    for ch in node_map:
        # 如果节点已经执行完成，跳过
        if ch in final_node:
            continue
        else:
            label = True
            next_node_list: list[str] = node_map[ch]["next"]
            for ch0 in next_node_list:
                if ch0 not in final_node:
                    label = False
                    break
            if label:
                run_node.append(node_map[ch]["index"])
    return run_node

