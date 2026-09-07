{
  'target_defaults': {
    'target_conditions': [
      ['_target_name=="abseil" and _toolset=="target"', {
        # musl's pthread waiter uses the futex operations Pedigree implements.
        'defines': ['ABSL_FORCE_WAITER_MODE=2'],
      }],
    ],
  },
}
