def app_http_login(s, proto, host, email, password):
    # 'pwd' is used by apps, 'password' is used by SSO
    login_data = {'submit':1, 'email': email, 'pwd': password, 'password': password}

    response = s.post(proto + '://' + host + '/admin/action/login.php', data=login_data, timeout=(10, 30))

    if response.url.find('?return_to') != -1:
        response = s.post(response.url, data=login_data, timeout=(10, 30))

    # we have HTTP error
    if response.status_code != 200:
        return False
    
    # returned to login page due to wrong user/pass
    if response.url.find('/login.php') > 0:
        return False
    # logged in
    return True
