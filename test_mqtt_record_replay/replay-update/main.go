// mqtt-record.go - tools for recording from and playing back to MQTT topics.
//
// License:
//
//	Copyright (c) 2018 yoggy <yoggy0@gmail.com>
//	Copyright (c) 2022 Jannik Beyerstedt <beyerstedt@consider-it.de>
//	Released under the MIT license
//	http://opensource.org/licenses/mit-license.php;
package main

import (
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"os"

	"os/signal"
	"time"

	"encoding/binary"
	//"errors"

	msgpack "github.com/vmihailenco/msgpack/v5"
	//"golang.org/x/term"
	mqtt "github.com/eclipse/paho.mqtt.golang"
)

const buildVersion string = "v2.1.0"

const PAUSE string = "pause"
const PLAY string = "play"
const FIVE_SEC_FORWARD string = "five sec forward"
const FIVE_SEC_BACKWARD string = "five sec backward"
const REPLAY_STOP string = "stop replay"
const START_BEGINNING string = "start beginning"

// configuration values
const skipSeconds int = 5

// configuration values
var verbosity int
var brokerURL string
var topic string
var filename string
var statsOutput bool
var versionMode bool
var startTimeSec uint
var endTimeSec uint // end time of 0 seconds doesn't make sense, so use it for "full file"
var payload string

// internal state
var shouldHalt bool
var shouldExit bool
var keepPlaying bool
var playFromBegin bool
var five_backward bool
var five_forwards bool

func init() {
	flag.IntVar(&verbosity, "v", 1, "verbosity level: off (0), info (1), debug (2)")

	flag.StringVar(&brokerURL, "b", "tcp://localhost:1883", "MQTT broker URL")
	flag.StringVar(&filename, "i", "", "Input file (REQUIRED)")
	flag.UintVar(&startTimeSec, "s", 0, "Starting time offset (seconds)")
	flag.UintVar(&endTimeSec, "e", 0, "End time (seconds, leave out for full file)")
	flag.BoolVar(&versionMode, "version", false, "Print version number")
	flag.Parse()

	if filename == "" && !versionMode {
		println("ERROR: Input file name not set!")
		println("Usage:")
		flag.PrintDefaults()
		os.Exit(1)
	}

	shouldHalt = false
	shouldExit = false
	keepPlaying = false
	playFromBegin = false
	five_backward = false
	five_forwards = false
}

func nowMillis() int64 {
	return time.Now().UnixNano() / int64(time.Millisecond)
}

type MqttMessage struct {
	Millis  int64
	Topic   string
	Payload []byte
}

func readEntry(file *os.File) (MqttMessage, int64) {
	// read payload size entry
	buf := make([]byte, binary.MaxVarintLen64)
	_, err := file.Read(buf)
	if err != nil {
		return MqttMessage{}, -1 // EOF reached
	}
	payload_size, _ := binary.Varint(buf)

	// read payload buffer
	payload_buf := make([]byte, payload_size)
	_, err = file.Read(payload_buf)
	if err != nil {
		return MqttMessage{}, -1 // EOF reached
	}

	// unpack message
	var msg MqttMessage
	err = msgpack.Unmarshal(payload_buf, &msg)
	if err != nil {
		log.Fatalln("Fatal error unpacking packet in recording file")
	}

	return msg, payload_size
}

func publish(client mqtt.Client, msg MqttMessage) {
	token := client.Publish(msg.Topic, byte(0), false, msg.Payload)
	token.Wait()
}

type Playback struct {
	File   *os.File
	Client mqtt.Client

	// internal playback state
	endTimeAvailable   bool
	endTimeMillis      int64
	recordingStartTime int64 // timestamp of first entry in file

	firstMsgMillis    int64
	firstMsgWallclock int64
	msgMillisRelative int64 // current playback position
	haltOffsetMillis  int64

	haltStartWallclock int64
}

func (p *Playback) Init(endTimeSec uint) {
	p.endTimeAvailable = endTimeSec > 0
	p.endTimeMillis = int64(endTimeSec) * 1000
}

func (p *Playback) PlayFrom(startTimeMillis uint) {
	// reset to file start when skipping backwards
	if int64(startTimeMillis) < p.msgMillisRelative {
		_, err := p.File.Seek(0, 0)
		if err != nil {
			log.Fatalln("Error selecting file start")
		}
	}

	// search for (new) start message when playback position has changed
	if startTimeMillis == 0 || int64(startTimeMillis) != p.msgMillisRelative {
		p.haltOffsetMillis = 0

		// get first entry in recording file
		msg, len := readEntry(p.File)
		if len < 0 {
			log.Println("End of recording reached")
			return
		}
		if p.recordingStartTime == 0 { // only set for very first call
			p.recordingStartTime = msg.Millis // timestamp of first entry in file
		}

		// fast forward to message at requested start time
		for {
			p.msgMillisRelative = msg.Millis - p.recordingStartTime
			if p.msgMillisRelative >= int64(startTimeMillis) {
				log.Printf("t=%6.2f s, %6d bytes, topic=%s\n", float32(p.msgMillisRelative)/1000.0, len, msg.Topic)
				publish(p.Client, msg)

				p.firstMsgMillis = msg.Millis
				p.firstMsgWallclock = nowMillis()

				break
			}

			msg, len = readEntry(p.File) // not at start time yet, skip to next message
			if len < 0 {
				log.Println("End of recording reached")
				return
			}
		}

	} else {
		// just re-start playing otherwise
		p.haltOffsetMillis = nowMillis() - p.haltStartWallclock
	}
}

func (p *Playback) SkipAndPlay(relativePlayPositionSec int) {
	currentPositionMillis := p.msgMillisRelative
	targetPositionMillis := currentPositionMillis + int64(relativePlayPositionSec*1000)
	if targetPositionMillis < 0 {
		targetPositionMillis = 0
	}

	p.PlayFrom(uint(targetPositionMillis))
}

func (p *Playback) PlayNextMessage() bool {
	msg, len := readEntry(p.File)
	if len < 0 {
		log.Println("End of recording reached")
		return false
	}

	p.msgMillisRelative = msg.Millis - p.recordingStartTime

	// check requested end time
	if p.endTimeAvailable && p.msgMillisRelative > p.endTimeMillis {
		log.Println("Requested end time reached")
		return false
	}

	// wait for target time to be reached
	targetWallclock := p.firstMsgWallclock + (msg.Millis - p.firstMsgMillis) + p.haltOffsetMillis
	for {
		if nowMillis() >= targetWallclock {
			log.Printf("t=%6.2f s, %6d bytes, topic=%s\n", float32(p.msgMillisRelative)/1000.0, len, msg.Topic)
			publish(p.Client, msg)
			break
		}

		time.Sleep(200 * time.Microsecond)
	}

	return true // still messages left
}

func (p *Playback) Pause() {
	p.haltStartWallclock = nowMillis()
}

var message_handler mqtt.MessageHandler = func(client mqtt.Client, msg mqtt.Message) {
	// Define the callback function when a message is received

	topic := msg.Topic()
	payload := string(msg.Payload())
	fmt.Printf("Received message: %s, %s\n", topic, payload)

	if topic == "mqtt-replay-record/replay" {
		if shouldHalt {
			if payload == PAUSE {
				fmt.Println(" already in pause mode .............")
			} else if payload == PLAY {
				keepPlaying = true
			}
		} else {
			if payload == PLAY {
				fmt.Println(" out of condition.............")
			} else if payload == PAUSE {
				shouldHalt = true
			}
		}

		if payload == REPLAY_STOP {
			shouldExit = true
		} else if payload == START_BEGINNING {
			playFromBegin = true
		} else if payload == FIVE_SEC_BACKWARD {
			five_backward = true
		} else if payload == FIVE_SEC_FORWARD {
			five_forwards = true
		} else {
			fmt.Println(" out of condition.............")
		}

	} else {
		fmt.Println("Unknown Topic.............")
	}
}

func main() {
	fmt.Println("MQTT Recordering player " + buildVersion)
	if versionMode {
		os.Exit(0)
	}

	fmt.Println("- MQTT broker:     ", brokerURL)
	fmt.Println("- Input filename:  ", filename)
	if endTimeSec > 0 {
		fmt.Println("- Interval:        ", startTimeSec, "-", endTimeSec, "sec.")
	} else if startTimeSec > 0 {
		fmt.Println("- Start time:      ", startTimeSec, "sec.")
	}

	fmt.Println("- Subscribe topic: ", topic)
	fmt.Println("- Output filename: ", filename)
	fmt.Println("")

	if verbosity < 1 {
		log.SetFlags(0)
		log.SetOutput(ioutil.Discard)
	}

	// try opening file for reading
	file, err := os.Open(filename)
	if err != nil {
		log.Fatalln("Error opening file for reading:", err)
	}
	defer file.Close()

	// subscribe to MQTT
	opts := mqtt.NewClientOptions()
	opts.AddBroker(brokerURL)
	opts.SetDefaultPublishHandler(message_handler)

	client := mqtt.NewClient(opts)
	defer client.Disconnect(100)
	if token := client.Connect(); token.Wait() && token.Error() != nil {
		log.Panicln("Error connecting to MQTT broker:", token.Error())
	}
	if verbosity > 1 {
		log.Println("Success connecting to MQTT broker")
	}

	// Subscribe to the "record" topic
	if token := client.Subscribe("mqtt-replay-record/replay", 0, nil); token.Wait() && token.Error() != nil {
		log.Fatalln("Error subscribing to MQTT topic:", token.Error())
	}
	if verbosity > 1 {
		log.Println("Success subscribing to topic")
	}

	// capture some signals
	signalChannel := make(chan os.Signal, 1)
	signal.Notify(signalChannel, os.Interrupt)

	//
	// process recording file
	//
	var playControl Playback
	playControl.File = file
	playControl.Client = client

	playControl.Init(endTimeSec)
	playControl.PlayFrom(startTimeSec * 1000)

	messagesLeft := true
	for messagesLeft && !shouldExit {
		fmt.Printf("message processing...........\n")
		fmt.Printf("should halt: %v..........\n", shouldHalt)

		for shouldHalt {
			playControl.Pause()

			if keepPlaying {
				// Check if payload is a string and equals "play"
				fmt.Printf("keep playing...........\n")
				playControl.SkipAndPlay(0)
				shouldHalt = false
				keepPlaying = false
				break
			} else if shouldExit {
				log.Println("Exit requested")
				log.Println("Replay finished")
				os.Exit(0)
			} else if five_backward {
				playControl.SkipAndPlay(-skipSeconds)
				shouldHalt = false
				five_backward = false
				break
			} else if five_forwards {
				playControl.SkipAndPlay(skipSeconds)
				shouldHalt = false
				five_forwards = false
				break
			} else if playFromBegin {
				playControl.PlayFrom(startTimeSec * 1000)
				shouldHalt = false
				playFromBegin = false
				break
			} else {
				fmt.Println("now is pausing.. wait for other commands.....")
			}
		}

		if playFromBegin {
			playControl.PlayFrom(startTimeSec * 1000)
			shouldHalt = false
			playFromBegin = false
		}

		if five_backward {
			playControl.SkipAndPlay(-skipSeconds)
			shouldHalt = false
			five_backward = false
		}

		if five_forwards {
			playControl.SkipAndPlay(skipSeconds)
			shouldHalt = false
			five_forwards = false
		}

		messagesLeft = playControl.PlayNextMessage()
	}

	log.Println("Exit requested")
	log.Println("Replay finished")
	os.Exit(0)
}

// for {
// 	select {
// 	case <-signalChannel:

// 		// Unsubscribe from the "replay" topic
// 		if token := client.Unsubscribe("mqtt-replay-record/record"); token.Wait() && token.Error() != nil {
// 			log.Fatal(token.Error())
// 			fmt.Printf("The client is not subscribe to the replay topic.......")
// 		}

// 		// Unsubscribe from the "record" topic
// 		if token := client.Unsubscribe("mqtt-replay-record/replay"); token.Wait() && token.Error() != nil {
// 			log.Fatal(token.Error())
// 			fmt.Printf("The client is not subscribe to the record topic ......")
// 		}

// 		// Disconnect from the MQTT broker
// 		client.Disconnect(250)
// 		fmt.Println("Disconnected from the MQTT broker.")
// 		time.Sleep(500 * time.Millisecond)
// 		return

// 	}

// }
