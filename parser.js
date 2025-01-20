function parseHtmlFile(htmlContent) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(htmlContent, 'text/html');

  // Find the section with "Copy of Your Data"
  const dataSection = Array.from(doc.querySelectorAll('h1')).find(h1 => h1.textContent === "Copy of Your Data");
  if (!dataSection) {
    throw new Error("Could not find Copy of Your Data section");
  }

  // Find the Call of Duty section
  const codHeading = Array.from(doc.querySelectorAll('h1')).find(h1 => h1.textContent.trim() === " Call of Duty: Black Ops 6");
  if (!codHeading) {
    throw new Error("Could not find Call of Duty: Black Ops 6 heading");
  }

  // Find the multiplayer data heading
  const mpHeading = Array.from(doc.querySelectorAll('h2')).find(h2 => h2.textContent === "Multiplayer Match Data (reverse chronological)");
  if (!mpHeading) {
    throw new Error("Could not find Multiplayer Match Data heading");
  }

  // Get the first table after the multiplayer heading
  const table = mpHeading.nextElementSibling;
  if (!table || table.tagName !== 'TABLE') {
    throw new Error("Could not find match data table");
  }

  // Get headers
  const headers = Array.from(table.querySelectorAll('th')).map(th => th.textContent.trim());

  // Get data rows
  const rows = Array.from(table.querySelectorAll('tr')).slice(1); // Skip header row
  const data = rows.map(row => {
    const cells = Array.from(row.querySelectorAll('td'));
    const rowData = {};
    cells.forEach((cell, i) => {
      rowData[headers[i]] = cell.textContent.trim();
    });
    return rowData;
  });

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
