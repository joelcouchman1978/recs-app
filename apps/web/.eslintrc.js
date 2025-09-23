module.exports = {
  root: true,
  extends: [],
  rules: {
    'no-restricted-imports': ['error', {
      patterns: [
        { group: ['**/apps/web/components/RecCard*', 'components/RecCard*'], message: 'Use @/components/RecCard from app/ only.' }
      ]
    }]
  }
}

