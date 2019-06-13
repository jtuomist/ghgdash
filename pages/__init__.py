class Page:
    def __init__(self, name, content, callbacks=[]):
        self.name = name
        self.content = content
        self.callbacks = callbacks


def page_callback(output, inputs=[], state=[]):
    def wrap_func(func):
        func.output = output
        func.inputs = inputs
        func.state = state
        return func

    return wrap_func
