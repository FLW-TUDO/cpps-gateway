async function renderTimeslots(workstationId) {
            let timeSlotOverwiev = document.getElementById( 'time-slot-overview' );
            let maxLength;
            while ( timeSlotOverwiev.hasChildNodes() ) {
                timeSlotOverwiev.removeChild(timeSlotOverwiev.firstChild);
            }
            let workstations = await fetch( 'http://192.168.2.188:27772/ws/api/workstations' )
                .then( function ( response ) {
                    return response.json();
                } );
            console.log(workstations);
            for ( let workstation of workstations ) {
                if( workstation.workstation_id === workstationId ) {
                    const calendarList = workstation.calendar;
                    if ( calendarList.length > 0 ) {
                        const firstStartTime = calendarList[0].desired_availability_date;
                        const lastEntry = calendarList[ calendarList.length - 1 ];
                        const lastEndTime = Math.round( lastEntry.desired_availability_date +
                                lastEntry.time_slot_length);
                        maxLength = Math.round(lastEndTime - firstStartTime + 500);
                        let deviation = 0;
                        for ( let i = 0; i < calendarList.length; i++ ) {
                            const entry = calendarList[ i ];
                            const previousEntry = calendarList[ i-1 ];
                            let row = document.createElement( 'div' );
                            let distance = document.createElement( 'div' );
                            let timeSlot = document.createElement( 'div' );
                            let info = document.createElement( 'div' );
                            let infoDistnaceSpan = document.createElement( 'span' );
                            let infoStartEndSpan = document.createElement( 'span' );
                            let hr = document.createElement( 'hr' );

                            const startTime = new Date( entry.desired_availability_date * 1000 );
                            let startHours = startTime.getHours();
                            let startMinutes = '0' + startTime.getMinutes();
                            let startSeconds = '0' + startTime.getSeconds();
                            const formattedStartTime = startHours + ':' +
                                startMinutes.substr(-2) + ':' + startSeconds.substr(-2);
                            const endTime = new Date( (entry.desired_availability_date + entry.time_slot_length) * 1000 );
                            let endHours = endTime.getHours();
                            let endMinutes = '0' + endTime.getMinutes();
                            let endSeconds = '0' + endTime.getSeconds();
                            const formattedEndTime = endHours + ':' +
                                endMinutes.substr(-2) + ':' + endSeconds.substr(-2);

                            let distanceLength;
                            let distanceBetween;
                            let timeSlotLength = entry.time_slot_length.toString() + 'px';
                            if( i === 0 ) {
                                distanceLength = '0px';
                                distanceBetween = 0;
                            } else {
                                const actualStartTime = entry.desired_availability_date;
                                const difference = actualStartTime - firstStartTime;
                                distanceLength = Math.round(difference).toString() + 'px';
                                distanceBetween = Math.round(actualStartTime -
                                    (previousEntry.desired_availability_date + previousEntry.time_slot_length - 2));
                            }

                            const infoText1 = document.createTextNode( 'Dist.: ' );
                            const infoText2 = document.createTextNode( distanceBetween.toString() + ' sec.' );
                            const infoText3 = document.createTextNode( ' | ID: ' + entry.id_task.toString() + '; ' +
                                entry.id_cycle + ' | ' );
                            const infoText4 = document.createTextNode( formattedStartTime + ' - ' + formattedEndTime );
                            row.style.display = 'flex';
                            row.style.order = i.toString();
                            distance.className = 'distance';
                            distance.style.width = distanceLength;
                            timeSlot.className = 'time-slot';
                            info.className = 'info';
                            timeSlot.style.width = timeSlotLength;
                            if( distanceBetween >= 0 ) {
                                infoDistnaceSpan.style.color = 'green'
                            } else {
                                infoDistnaceSpan.style.color = 'red'
                            }
                            infoStartEndSpan.style.color = 'black';
                            distance.appendChild( hr );
                            row.appendChild( distance );
                            row.appendChild( timeSlot );
                            info.appendChild( infoText1 );
                            infoDistnaceSpan.appendChild( infoText2 );
                            info.appendChild( infoDistnaceSpan );
                            info.appendChild( infoText3 );
                            infoStartEndSpan.appendChild( infoText4 );
                            info.appendChild( infoStartEndSpan );
                            row.appendChild( info );
                            timeSlotOverwiev.appendChild( row );
                        }
                    } else {
                        let text = document.createElement( 'p' );
                        text.innerText = '<empty>';
                        timeSlotOverwiev.appendChild( text );
                    }

                    break;
                }
            }
            if( maxLength !== undefined && maxLength!== null && maxLength > 300) {
                 timeSlotOverwiev.style.width = maxLength.toString() + 'px';
            }
        }

        async function loadButtons() {
            let buttonOverview = document.getElementById( 'button-overview' );
            let workstations = await fetch( 'http://192.168.2.188:27772/ws/api/workstations' )
                .then( function ( response ) {
                    return response.json();
                } );
            for ( let workstation of workstations ) {
                const workstationId = workstation.workstation_id
                let button = document.createElement( 'button' );
                const buttonText = document.createTextNode( workstationId );
                button.addEventListener( 'click', function () {
                    renderTimeslots( workstationId )
                } );
                button.appendChild( buttonText );
                buttonOverview.appendChild( button );
            }
        }