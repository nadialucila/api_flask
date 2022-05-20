export default function login() {
    const axios = require('axios').default;

    const loguearse =  () => {

        let emailLogin = document.getElementById('email').nodeValue;
        let passLogin = document.getElementById('pass').nodeValue;

        axios.post('http://127.0.0.1:5000/api/login', {
        email: emailLogin,
        pass: passLogin
        })
        .then(function (response) {
        console.log(response);
        })
        .catch(function (error) {
        console.log(error);
    });
    }

    return (
        <div>

        </div>
    );
}