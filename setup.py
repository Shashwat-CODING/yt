#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="youtube-audio-player",
    version="0.1.0",
    description="A Python-based YouTube audio player that allows you to search, extract, and play audio from YouTube videos",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/youtube-audio-player",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "flask>=3.1.0",
        "flask-cors>=5.0.1",
        "innertube>=2.1.16",
        "pyaudio>=0.2.14",
        "pytube>=15.0.0",
        "requests>=2.32.3",
        "rich>=13.9.4",
    ],
    entry_points={
        "console_scripts": [
            "youtube-terminal=youtube_audio_player:main",
            "youtube-web=web_app:app.run",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Sound/Audio :: Players",
    ],
    python_requires=">=3.11",
    keywords="youtube, audio, player, music, streaming",
    license="MIT",
)