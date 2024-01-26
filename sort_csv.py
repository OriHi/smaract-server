#%%
import os

# Specify the directory where your .csv files are located
directory = '/home/ori/Documents/Work/Smaract/graphene_1mm_10um/'

# Loop through the range of files you have (1-1.csv to 1-1000.csv)
for i in range(1, 1001):
    try:
    # Generate the old and new file names
        old_filename = os.path.join(directory, f'1-{i}.csv')
        new_filename = os.path.join(directory, f'{(i//100) + 1}-{i%10 + 1}.csv')

        # Rename the file
        os.rename(old_filename, new_filename)
    except Exception as e:
        print(f"Error: {e}")

print("Files successfully renamed.")
# %%
