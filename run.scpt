tell application "iTerm"
	tell current window
		set my_path to "cd Documents/UNSW/COMP\\ 9331/Assignments/"
		create tab with default profile
		tell current session
			set name to "Peer1"
			write text my_path
			write text "python3 cdht.py 1 3 4"
		end tell
		create tab with default profile
		tell current session
			set name to "Peer3"
			write text my_path
			write text "python3 cdht.py 3 4 5"
		end tell
		create tab with default profile
		tell current session
			set name to "Peer4"
			write text my_path
			write text "python3 cdht.py 4 5 8"
		end tell
		create tab with default profile
		tell current session
			set name to "Peer5"
			write text my_path
			write text "python3 cdht.py 5 8 10"
		end tell
		create tab with default profile
		tell current session
			set name to "Peer8"
			write text my_path
			write text "python3 cdht.py 8 10 12"
		end tell
		create tab with default profile
		tell current session
			set name to "Peer10"
			write text my_path
			write text "python3 cdht.py 10 12 15"
		end tell
		create tab with default profile
		tell current session
			set name to "Peer12"
			write text my_path
			write text "python3 cdht.py 12 15 1"
		end tell
		create tab with default profile
		tell current session
			set name to "Peer15"
			write text my_path
			write text "python3 cdht.py 15 1 3"
		end tell
	end tell
end tell