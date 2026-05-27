from fastapi import Request

def get_display(request: Request):
    return request.app.state.display