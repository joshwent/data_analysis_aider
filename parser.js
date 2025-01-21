function parseHtmlFile(htmlContent) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlContent, 'text/html');

    // Parse BO6 data
    function parseBO6Data() {
        const bo6Heading = Array.from(doc.querySelectorAll('h2')).find(h2 => 
            h2.textContent === "Multiplayer Match Data (reverse chronological)" && 
            h2.previousElementSibling.textContent.includes("Black Ops 6")
        );
        if (!bo6Heading) {
            throw new Error("Could not find BO6 Match Data heading");
        }

        const table = bo6Heading.nextElementSibling;
        if (!table || table.tagName !== 'TABLE') {
            throw new Error("Could not find BO6 match data table");
        }

        return parseTable(table);
    }

    // Parse MW3 data
    function parseMW3Data() {
        const mw3Heading = Array.from(doc.querySelectorAll('h2')).find(h2 => 
            h2.textContent === "Multiplayer Match Data (reverse chronological)" && 
            h2.previousElementSibling.textContent.includes("Modern Warfare 3")
        );
        if (!mw3Heading) {
            throw new Error("Could not find MW3 Match Data heading");
        }

        const table = mw3Heading.nextElementSibling;
        if (!table || table.tagName !== 'TABLE') {
            throw new Error("Could not find MW3 match data table");
        }

        return parseTable(table);
    }

    // Helper function to parse any table
    function parseTable(table) {
        const headers = Array.from(table.querySelectorAll('th')).map(th => th.textContent.trim());
        const rows = Array.from(table.querySelectorAll('tr')).slice(1);
        const data = rows.map(row => {
            const cells = Array.from(row.querySelectorAll('td'));
            const rowData = {};
            cells.forEach((cell, i) => {
                rowData[headers[i]] = cell.textContent.trim();
            });
            return rowData;
        });

        return data;
    }

    return {
        bo6Data: parseBO6Data(),
        mw3Data: parseMW3Data()
    };

  // Convert numeric fields
  const numericColumns = [
    'Score', 'Kills', 'Deaths', 'Shots', 'Hits', 'Headshots',
    'Damage Done', 'Damage Taken', 'Longest Streak', 'Lifetime Kills',
    'Lifetime Deaths', 'Lifetime Time Played', 'Assists', 'Executions',
    'Suicides', 'Armor Collected', 'Armor Equipped', 'Armor Destroyed',
    'Ground Vehicles Used', 'Air Vehicles Used', 'Total XP', 'Score XP',
    'Challenge XP', 'Match XP', 'Medal XP', 'Bonus XP', 'Misc XP',
    'Accolade XP', 'Weapon XP', 'Operator XP', 'Clan XP', 'Battle Pass XP',
    'Rank at Start', 'Rank at End', 'XP at Start', 'XP at End',
    'Score at Start', 'Score at End', 'Prestige at Start', 'Prestige at End',
    'Lifetime Wall Bangs', 'Lifetime Games Played', 'Lifetime Wins',
    'Lifetime Losses', 'Lifetime Hits', 'Lifetime Misses', 'Lifetime Near Misses',
    'Skill'
  ];

  data.forEach(row => {
    numericColumns.forEach(col => {
      if (col in row) {
        row[col] = parseFloat(row[col]) || 0;
      }
    });

    // Convert timestamps
    ['UTC Timestamp', 'Match Start Timestamp', 'Match End Timestamp'].forEach(col => {
      if (col in row) {
        row[col] = new Date(row[col]);
      }
    });
  });

  return data;
}
