from fastapi import Request

def get_display(request: Request):
    return request.app.state.display

def get_rate_limiter(request: Request):
    return request.app.state.rate_limiter

def get_app_loader(request: Request):
    return request.app.state.app_loader