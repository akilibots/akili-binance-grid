# Welcome to akili-grid!

### Built specifically for high frequency trading using zero fee pairs in Binance

[![stability-alpha](https://img.shields.io/badge/stability-alpha-f4d03f.svg)](https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#alpha)
[![Telegram](https://badges.aleen42.com/src/telegram.svg)](https://t.me/+9F0CZj8emLc2YTY0)

Jambo! and welcome! akiligrid is a grid bot that uses the grid strategy to trade crypto currencies. The word **akili** means brain or mind in Swahili. The objective here is to make it the most intelligent grid bot in existence that has as many advanced features as possible, but which at the same time can be used by your typical crypto trader with basic grid bot experience

As with all projects was born out of frustration on the lack of features with "commercial" bots out there. They always missed that little tweak that in my mind would make things a lot more better, and hopefully profitable.

This is a high frequency trading bot built to take advantage of Binance zero fees on BTC/BUSD and thus the bot orders can be very tight. I've had success running it only 2 USD above and below the current price off a server in Japan and can easily do 100 orders per minute, and because there are zero fees, there isn't any theoretical minumum of how small the grid orders or spacing can be.

Let's get the usual out of the way...

***DISCLAIMER

This software is for educational purposes only. Do not risk money which you are afraid to lose. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS.***

It takes the current BTC/BUSD price and builds a very tight grid around it configured by the environment variables.
Please beware that it will run until the cows come home so keep monitoring. Suggest you connect your telegram for this. For best performance run it off a server in Osaka, Japan (Linode / Oracle / AWS) for low latency which returns better results for high frequency trading as the binance API servers are also somewhere in Osaka or Tokyo