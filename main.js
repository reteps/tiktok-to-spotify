const axios = require('axios')
const tiktok = require('tiktok-scraper')
// const url = 'https://vm.tiktok.com/ZMJwNwEoc/'
// const url = 'https://vm.tiktok.com/ZMJwY53gV/'
// const url = 'https://vm.tiktok.com/ZMJwY87XF/'
// const url = 'https://vm.tiktok.com/ZMJwYkMF3/'
const urls = [
    'https://vm.tiktok.com/ZMJwm6Kva',
    'https://vm.tiktok.com/ZMJwY53gV/',
    'https://vm.tiktok.com/ZMJwY87XF/',
    'https://vm.tiktok.com/ZMJwYkMF3/',
    'https://vm.tiktok.com/ZMJwNwEoc/'

]
const fs = require('fs')
let n = 0
for (let url of urls) {
    tiktok.getVideoMeta(url).then(x => {
        return axios.get(x.collector[0].videoUrl, {
            headers: x.headers,
            responseType: 'stream'
        })
    }).then(response => {
        response.data.pipe(fs.createWriteStream(`out${n}.mp4`))
        n++
    }).catch(err => {
        console.log(err)
    })
}