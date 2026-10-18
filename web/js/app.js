import {login,logout} from './api.js';
import {startSteps} from './steps.js';
const loginView=document.querySelector('#login'), workspace=document.querySelector('#workspace'), form=document.querySelector('#login-form'), error=document.querySelector('#login-error');
function show(){loginView.hidden=true;workspace.hidden=false;startSteps()}
form.addEventListener('submit',async e=>{e.preventDefault();error.textContent='';const data=new FormData(form);try{await login(data.get('username'),data.get('password'));show()}catch(err){error.textContent=err.message}});
document.querySelector('#logout').onclick=async()=>{await logout();workspace.hidden=true;loginView.hidden=false;form.reset()};
