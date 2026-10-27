function run() {
	var app = Application.currentApplication()
	app.includeStandardAdditions = true

	var appPath = app.pathTo(this)
	var version = 'v1.5.2'
	try {
		version = 'v' + app.doShellScript(`defaults read '${appPath}/Contents/Info.plist' CFBundleShortVersionString`)
	} catch (e) {}

	// Check for updates non-blockingly with timeout
	try {
		var latestVersion = app.doShellScript(`curl -s -m 3 -H "User-Agent: ChargeLimiter" 'https://api.github.com/repos/itsjoshpark/charge-limiter/releases/latest' | awk -F '"' '/tag_name/{print $4}'`)
		var url = 'https://github.com/itsjoshpark/charge-limiter/releases/latest'

		if (latestVersion && version !== latestVersion && latestVersion.indexOf('v') === 0) {
			var alertRes = app.displayAlert(`A new version of Charge Limiter is available!`, {
				message: `Charge Limiter ${latestVersion} is now available—you have ${version}. Would you like to get the update?`,
				as: 'informational',
				buttons: ['Remind Me Later', 'Get Update'],
				defaultButton: 'Get Update'
			})
			if (alertRes.buttonReturned === 'Get Update') {
				app.doShellScript(`open '${url}'`)
			}
		}
	} catch (e) {}

	var parentPath = appPath + '/Contents/Resources'
	var helperInstallDir = '/Library/Application Support/ChargeLimiter'
	var helperInstalledPath = helperInstallDir + '/bclm'
	var bundledHelperPath = parentPath + '/bclm'

	// Determine helper to read current charge level
	var readCmd = `'${bundledHelperPath}' read`
	try {
		if (app.doShellScript(`test -x '${helperInstalledPath}' && echo "yes" || echo "no"`) === 'yes') {
			readCmd = `'${helperInstalledPath}' read`
		}
	} catch (e) {}

	var chargeLevel = '100'
	try {
		chargeLevel = app.doShellScript(readCmd)
	} catch (e) {
		try {
			chargeLevel = app.doShellScript(`'${bundledHelperPath}' read`)
		} catch (e2) {}
	}

	var response
	try {
		response = app.displayDialog(`This utility allows you to set the maximum battery charge limit.\n\nThe current charge limit is: ${chargeLevel}%\n\nCharge Limit (40-100, default is 100):`, {
			withTitle: `Charge Limiter ${version}`,
			defaultAnswer: chargeLevel || '80',
			buttons: ['Close', 'Set Charge Limit'],
			defaultButton: 'Set Charge Limit',
			cancelButton: 'Close'
		})
	} catch (e) {
		// User clicked Close or Cancel
		return
	}

	var enteredText = (response.textReturned || '').trim()
	var value = Number(enteredText)

	if (isNaN(value) || value < 40 || value > 100) {
		app.displayDialog('Please enter a valid number from 40 to 100.', {
			withTitle: `Charge Limiter ${version}`,
			buttons: ['OK'],
			defaultButton: 'OK'
		})
		return
	}

	try {
		// Execute everything in a single atomic script under administrator privileges:
		// 1. Install helper tool to persistent system location to prevent AppTranslocation / quarantine issues
		// 2. Set proper root:wheel ownership and strip quarantine flags
		// 3. Write charge limit to SMC
		// 4. Update launch daemon persistence cleanly
		var script = [
			`mkdir -p '${helperInstallDir}'`,
			`cp -f '${bundledHelperPath}' '${helperInstalledPath}'`,
			`chown root:wheel '${helperInstalledPath}'`,
			`chmod 755 '${helperInstalledPath}'`,
			`xattr -d com.apple.quarantine '${helperInstalledPath}' 2>/dev/null || true`,
			`'${helperInstalledPath}' write ${value}`,
			(value === 100 ? `'${helperInstalledPath}' unpersist` : `'${helperInstalledPath}' persist`)
		].join(' && ')

		app.doShellScript(script, { administratorPrivileges: true })

		if (value === 100) {
			app.displayDialog(`Success!\n\nThe battery charge limit has been removed and persistence disabled. Your Mac will now fully charge.`, {
				withTitle: `Charge Limiter ${version}`,
				buttons: ['OK'],
				defaultButton: ['OK']
			})
		} else {
			app.displayDialog(`Success!\n\nCharge limit set to ${value}%.\n\nIf your MacBook currently has more than ${value}% charge, leave the charger unplugged until the battery level drops below ${value}%. Afterwards, your battery will not charge beyond ${value}%.`, {
				withTitle: `Charge Limiter ${version}`,
				buttons: ['OK'],
				defaultButton: ['OK']
			})
		}
	} catch (e) {
		// If the user cancelled the password prompt (error -128), exit quietly
		if (e.errorNumber === -128 || (e.message && e.message.indexOf("User canceled") !== -1)) {
			return
		}

		app.displayDialog(`There was a problem setting the charge limit:\n\n${e.message || e}`, {
			withTitle: `Charge Limiter ${version}`,
			buttons: ['OK'],
			defaultButton: ['OK']
		})
	}
}
