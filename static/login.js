
let h = new Headers()
h.append('Accept','application/json')
h.append('Content-Type','application/json')
h.append('Authorization','')

let token = ''

export default function loguearse() {
  h.set('Content-Type','application/json')

  let emailLogin = document.getElementById('email').value
  let passLogin = document.getElementById('pass').value

  fetch("http://127.0.0.1:5000/api/login", {
  method: 'POST',
  headers: h,
  body: JSON.stringify({
    email: emailLogin,
    pass: passLogin
  })
  })
  .then( response => response.json()
  .then( data => {
    localStorage.setItem("Authorization", data['token'])
    token = data['token']
    index()
  }))

}

function index() {
  fetch("http://127.0.0.1:5000/", {
  method: 'GET',
  headers: {
      'Authorization': token,
      'Content-Type': 'text/html',
      'Accept': 'text/html'
  }
  })
  .then( response => response.text()
  .then( data => {

  }))
}




